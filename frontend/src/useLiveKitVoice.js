import { useState, useRef, useEffect, useCallback } from 'react';
import { Room, RoomEvent, Track } from 'livekit-client';

// Always capture from the system's default microphone
const AUDIO_CAPTURE = { autoGainControl: true, echoCancellation: true, noiseSuppression: true, deviceId: 'default' };

export function useLiveKitVoice() {
  const [status, setStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [volume, setVolume] = useState(0.0);
  const [error, setError] = useState(null);
  // Live transcript of the call: [{ id, role: 'user' | 'assistant', text, final }]
  const [transcript, setTranscript] = useState([]);
  
  const roomRef = useRef(null);
  const audioElementRef = useRef(null);

  // Setup hidden audio element for WebRTC playback
  useEffect(() => {
    if (!audioElementRef.current) {
      const audio = document.createElement('audio');
      audio.autoplay = true;
      audio.style.display = 'none';
      document.body.appendChild(audio);
      audioElementRef.current = audio;
    }

    return () => {
      if (audioElementRef.current) {
        audioElementRef.current.remove();
        audioElementRef.current = null;
      }
      if (roomRef.current) {
        roomRef.current.disconnect();
        roomRef.current = null;
      }
    };
  }, []);

  const connect = useCallback(async (roomName = 'agri-room-1', language = 'hi-IN') => {
    try {
      setStatus('connecting');
      setError(null);
      setTranscript([]);

      // 1. Fetch WebRTC participant access token from FastAPI
      const res = await fetch(`/api/token?room=${encodeURIComponent(roomName)}&language=${encodeURIComponent(language)}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Token request failed with status ${res.status}`);
      }
      const data = await res.json();
      const { serverUrl, token } = data;

      // 2. Initialize LiveKit Room instance
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: AUDIO_CAPTURE
      });
      roomRef.current = room;

      // 3. Register Track Subscribed Event (Handle Incoming Agent Spoken Audio)
      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === Track.Kind.Audio && audioElementRef.current) {
          track.attach(audioElementRef.current);
          console.log('[LiveKit] Attached agent audio track to HTML5 player');
        }
      });

      // 4. Track Active Speakers (Visualizer states & Volume for 3D AIBlob)
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        const localSpeaker = speakers.find((s) => s.isLocal);
        const agentSpeaker = speakers.find((s) => !s.isLocal);
        const localSpeaking = Boolean(localSpeaker);
        const agentSpeaking = Boolean(agentSpeaker);

        setIsUserSpeaking(localSpeaking);
        setIsAgentSpeaking(agentSpeaking);

        if (agentSpeaking) {
          setVolume(Math.max(agentSpeaker.audioLevel || 0.65, 0.4));
        } else if (localSpeaking) {
          setVolume(Math.max(localSpeaker.audioLevel || 0.5, 0.3));
        } else {
          setVolume(0.0);
        }
      });

      // 5. Live transcripts: the agent publishes both sides on the 'lk.transcription' text-stream
      // topic, sent under the speaker's identity. Agent turns arrive as one growing stream per
      // segment; user turns arrive as a fresh full-text stream per update of the same segment.
      room.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
        const attrs = reader.info.attributes || {};
        const id = attrs['lk.segment_id'] || reader.info.id;
        const role = participantInfo.identity === room.localParticipant.identity ? 'user' : 'assistant';
        const upsert = (text, final) => setTranscript(prev => {
          const i = prev.findIndex(line => line.id === id);
          if (i === -1) return text ? [...prev, { id, role, text, final }] : prev;
          const next = prev.slice();
          next[i] = { ...next[i], text, final };
          return next;
        });
        let text = '';
        for await (const chunk of reader) {
          text += chunk.trim().startsWith('{') ? (() => { try { return JSON.parse(chunk).text ?? chunk; } catch { return chunk; } })() : chunk;
          upsert(text, false);
        }
        upsert(text, true);
      });

      // 6. Follow the system default microphone. On Chrome the library does not move the call
      // when the default mic changes or the mic in use is unplugged, so the call would keep
      // sending silence from the old device. Re-acquire the default mic whenever devices change.
      room.on(RoomEvent.MediaDevicesChanged, async () => {
        try {
          const track = room.localParticipant.getTrackPublication(Track.Source.Microphone)?.track;
          await track?.restartTrack(AUDIO_CAPTURE);
          console.log('[LiveKit] Microphones changed; call now uses the system default mic');
        } catch (e) {
          console.warn('[LiveKit] Could not switch to the new default microphone:', e);
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log('[LiveKit] Room disconnected');
        setStatus('disconnected');
        setIsAgentSpeaking(false);
        setIsUserSpeaking(false);
        setVolume(0.0);
      });

      // 7. Connect to LiveKit Cloud Room
      await room.connect(serverUrl, token);
      console.log('[LiveKit] Connected to room:', room.name);

      // 8. Enable the system default microphone
      await room.localParticipant.setMicrophoneEnabled(true, AUDIO_CAPTURE);
      console.log('[LiveKit] Microphone track published successfully');

      setStatus('connected');
    } catch (err) {
      console.error('[LiveKit] Voice connection error:', err);

      // Common WebRTC failures map to i18n keys (err_*) that the UI shows in the farmer's language
      let friendlyMsg = err.message || 'Failed to connect voice session';
      const name = err.name || '';
      if (name === 'NotFoundError' || friendlyMsg.includes('not found') || friendlyMsg.includes('Requested device')) {
        friendlyMsg = 'err_mic_not_found';
      } else if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || friendlyMsg.includes('denied')) {
        friendlyMsg = 'err_mic_denied';
      } else if (name === 'NotReadableError') {
        friendlyMsg = 'err_mic_busy';
      } else if (name === 'OverconstrainedError') {
        friendlyMsg = 'err_mic_unsupported';
      } else if (friendlyMsg.includes('LIVEKIT_URL') || friendlyMsg.includes('500')) {
        friendlyMsg = 'err_server_config';
      }

      setError(friendlyMsg);
      setStatus('error');
      if (roomRef.current) {
        roomRef.current.disconnect();
        roomRef.current = null;
      }
    }
  }, []);

  const disconnect = useCallback(() => {
    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    setStatus('disconnected');
    setIsAgentSpeaking(false);
    setIsUserSpeaking(false);
    setVolume(0.0);
  }, []);

  return {
    status,
    isAgentSpeaking,
    isUserSpeaking,
    volume,
    error,
    transcript,
    connect,
    disconnect,
    room: roomRef.current,
  };
}

