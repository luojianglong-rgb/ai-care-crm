import { useEffect, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  className?: string;
}

const VoiceInputButton = ({ onTranscript, className = '' }: VoiceInputButtonProps) => {
  const { isListening, isSupported, transcript, interimTranscript, startListening, stopListening, error } = useSpeechRecognition();
  const prevTranscriptRef = useRef('');

  // 当 transcript 变化时回调
  useEffect(() => {
    if (transcript && transcript !== prevTranscriptRef.current) {
      onTranscript(transcript);
      prevTranscriptRef.current = transcript;
    }
  }, [transcript, onTranscript]);

  const handleClick = () => {
    if (!isSupported) {
      alert('您的浏览器不支持语音输入，请使用输入法自带的语音功能');
      return;
    }
    if (isListening) {
      stopListening();
    } else {
      prevTranscriptRef.current = '';
      startListening();
    }
  };

  if (!isSupported) {
    return (
      <button type="button" onClick={handleClick} className={`p-1.5 text-slate-300 cursor-not-allowed ${className}`} title="浏览器不支持语音输入">
        <MicOff className="w-4 h-4" />
      </button>
    );
  }

  return (
    <div className="relative inline-flex flex-col items-center">
      <button type="button" onClick={handleClick}
        className={`relative p-1.5 rounded-lg transition-colors ${
          isListening
            ? 'text-red-500 bg-red-50 hover:bg-red-100'
            : 'text-emerald-600 hover:bg-emerald-50'
        } ${className}`}
        title={isListening ? '点击停止' : '点击开始语音输入'}
      >
        {isListening && (
          <span className="absolute inset-0 rounded-lg bg-red-400 opacity-30 animate-ping" />
        )}
        <Mic className="w-4 h-4 relative z-10" />
      </button>
      {isListening && interimTranscript && (
        <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded-lg whitespace-nowrap max-w-48 truncate z-20">
          {interimTranscript}
        </div>
      )}
      {error && (
        <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 bg-red-600 text-white text-xs px-2 py-1 rounded-lg whitespace-nowrap z-20">
          {error}
        </div>
      )}
    </div>
  );
};

export default VoiceInputButton;
