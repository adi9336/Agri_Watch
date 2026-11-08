import { useState, useRef, useEffect, useCallback } from 'react';
import { Room, RoomEvent, Track } from 'livekit-client';

export function useLiveKitVoice() {
  const [status, setStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [volume, setVolume] = useState(0.0);
  const [error, setError] = useState(null);
  
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
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        }
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

      room.on(RoomEvent.Disconnected, () => {
        console.log('[LiveKit] Room disconnected');
        setStatus('disconnected');
        setIsAgentSpeaking(false);
        setIsUserSpeaking(false);
        setVolume(0.0);
      });

      // 5. Connect to LiveKit Cloud Room
      await room.connect(serverUrl, token);
      console.log('[LiveKit] Connected to room:', room.name);

      // 6. Enable Local Microphone Track
      await room.localParticipant.setMicrophoneEnabled(true);
      console.log('[LiveKit] Microphone track published successfully');

      setStatus('connected');
    } catch (err) {
      console.error('[LiveKit] Voice connection error:', err);

      // Friendly Hindi error messages for common WebRTC failures
      let friendlyMsg = err.message || 'Failed to connect voice session';
      const name = err.name || '';
      if (name === 'NotFoundError' || friendlyMsg.includes('not found') || friendlyMsg.includes('Requested device')) {
        friendlyMsg = 'माइक नहीं मिला — कृपया माइक कनेक्ट करें और ब्राउज़र परमिशन दें';
      } else if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || friendlyMsg.includes('denied')) {
        friendlyMsg = 'माइक की परमिशन नहीं दी — ब्राउज़र में माइक एक्सेस Allow करें';
      } else if (name === 'NotReadableError') {
        friendlyMsg = 'माइक पहले से किसी दूसरे ऐप में उपयोग हो रहा है — बंद करके पुनः प्रयास करें';
      } else if (name === 'OverconstrainedError') {
        friendlyMsg = 'ऑडियो सेटिंग्स में समस्या — माइक सपोर्ट नहीं है';
      } else if (friendlyMsg.includes('LIVEKIT_URL') || friendlyMsg.includes('500')) {
        friendlyMsg = 'LiveKit सर्वर कॉन्फ़िगर नहीं है — .env में LIVEKIT_URL जोड़ें';
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
    connect,
    disconnect,
    room: roomRef.current,
  };
}

