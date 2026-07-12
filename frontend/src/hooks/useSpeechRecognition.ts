import { useState, useRef, useCallback, useEffect } from 'react';

const SpeechRecognitionAPI =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

const ERROR_MESSAGES: Record<string, string> = {
  'no-speech': '未检测到语音，请重试',
  'audio-capture': '无法访问麦克风，请检查权限',
  'not-allowed': '麦克风权限被拒绝，请在浏览器设置中允许',
  'network': '网络错误，语音识别需要网络连接',
};

const MAX_RETRIES = 3;

export function useSpeechRecognition(lang = 'zh-CN') {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const manualStopRef = useRef(false);
  const retryCountRef = useRef(0);

  const isSupported = !!SpeechRecognitionAPI;

  const stopListening = useCallback(() => {
    manualStopRef.current = true;
    recognitionRef.current?.stop();
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const startListening = useCallback(() => {
    if (!SpeechRecognitionAPI) return;

    // 停掉可能存在的旧会话
    recognitionRef.current?.abort();

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    manualStopRef.current = false;
    retryCountRef.current = 0;
    setError(null);
    setTranscript('');
    setInterimTranscript('');

    recognition.onstart = () => setIsListening(true);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let final = '';
      let interim = '';
      for (let i = 0; i < event.results.length; i++) {
        const r = event.results[i];
        if (r.isFinal) {
          final += r[0].transcript;
        } else {
          interim += r[0].transcript;
        }
      }
      if (final) setTranscript(final);
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'aborted') return;
      setError(ERROR_MESSAGES[event.error] || `语音识别错误: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      if (!manualStopRef.current && retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current++;
        try { recognition.start(); } catch { setIsListening(false); }
      } else {
        setIsListening(false);
      }
    };

    try {
      recognition.start();
    } catch {
      setError('无法启动语音识别');
      setIsListening(false);
    }

    recognitionRef.current = recognition;
  }, [lang]);

  // cleanup on unmount
  useEffect(() => {
    return () => { recognitionRef.current?.abort(); };
  }, []);

  return { isListening, isSupported, transcript, interimTranscript, startListening, stopListening, error };
}
