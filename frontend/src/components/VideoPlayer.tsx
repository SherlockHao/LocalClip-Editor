import React, { useEffect, useState, useRef as useReactRef } from 'react';

interface VideoPlayerProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  src: string;
  onTimeUpdate: () => void;
  onLoadedMetadata: () => void;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  audioSrc?: string | null;
  useExternalAudio?: boolean;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoRef,
  src,
  onTimeUpdate,
  onLoadedMetadata,
  isPlaying,
  currentTime,
  duration,
  audioSrc = null,
  useExternalAudio = false
}) => {
  const [hasLoaded, setHasLoaded] = useState(false);
  const audioRef = useReactRef<HTMLAudioElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdateEvent = () => onTimeUpdate();
    const handleLoadedMetadataEvent = () => {
      onLoadedMetadata();
      setHasLoaded(true);
    };

    video.addEventListener('timeupdate', handleTimeUpdateEvent);
    video.addEventListener('loadedmetadata', handleLoadedMetadataEvent);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdateEvent);
      video.removeEventListener('loadedmetadata', handleLoadedMetadataEvent);
    };
  }, [videoRef, onTimeUpdate, onLoadedMetadata]);

  // 同步视频和音频的播放/暂停
  useEffect(() => {
    const video = videoRef.current;
    const audio = audioRef.current;
    if (!video) return;

    if (isPlaying) {
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // 播放失败，静默处理
        });
      }

      // 如果使用外部音频，先同步时间再播放
      if (useExternalAudio && audio && audioSrc) {
        const targetTime = video.currentTime;
        const currentAudioTime = audio.currentTime;
        const timeDiff = Math.abs(targetTime - currentAudioTime);

        // 如果时间差距很小，直接播放
        if (timeDiff < 0.1) {
          audio.play().catch(err => console.error('外部音频播放失败:', err));
        } else {
          // 否则，先设置时间，等待seeked事件后再播放
          const handleSeeked = () => {
            audio.play().catch(err => console.error('外部音频播放失败:', err));
            audio.removeEventListener('seeked', handleSeeked);
          };

          audio.addEventListener('seeked', handleSeeked);
          audio.currentTime = targetTime;
        }
      }
    } else {
      video.pause();
      if (audio) {
        audio.pause();
      }
    }
  }, [isPlaying, useExternalAudio]);

  // 同步外部音频的时间
  useEffect(() => {
    const video = videoRef.current;
    const audio = audioRef.current;
    if (!video || !audio || !useExternalAudio || !audioSrc) return;

    const syncAudioTime = () => {
      const timeDiff = Math.abs(audio.currentTime - video.currentTime);
      if (timeDiff > 0.1) {
        const wasPlaying = !audio.paused;
        audio.currentTime = video.currentTime;
        // 如果音频之前在播放，确保同步后继续播放
        if (wasPlaying && !video.paused) {
          audio.play().catch(err => console.error('恢复播放失败:', err));
        }
      }
    };

    video.addEventListener('seeked', syncAudioTime);
    return () => {
      video.removeEventListener('seeked', syncAudioTime);
    };
  }, [videoRef, useExternalAudio, audioSrc]);

  // 处理音频源切换（只负责静音/取消静音视频）
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (useExternalAudio && audioSrc) {
      video.muted = true;
    } else {
      video.muted = false;
    }
  }, [useExternalAudio, audioSrc]);

  return (
    <div className="w-full h-full flex items-center justify-center relative bg-black">
      <video
        ref={videoRef}
        src={src}
        className="max-w-full max-h-full object-contain"
        onPlay={() => {}}
        onPause={() => {}}
        playsInline
        preload="metadata"
      />
      {/* 外部音频元素 */}
      {audioSrc && (
        <audio
          ref={audioRef}
          src={audioSrc}
          preload="auto"
          style={{ display: 'none' }}
          onError={(e) => console.error('音频加载错误', e)}
        />
      )}
    </div>
  );
};

export default VideoPlayer;