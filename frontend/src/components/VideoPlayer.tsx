import React, { useEffect, useState, useCallback } from 'react';

interface VideoPlayerProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  src: string;
  onTimeUpdate: () => void;
  onLoadedMetadata: () => void;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoRef,
  src,
  onTimeUpdate,
  onLoadedMetadata,
  isPlaying,
  currentTime,
  duration
}) => {
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdateEvent = () => onTimeUpdate();
    const handleLoadedMetadataEvent = () => {
      onLoadedMetadata();
      setHasLoaded(true);
    };
    const handleError = (e) => {
      console.error("视频加载错误:", e);
    };
    const handleSeeking = () => {
      console.log('[VideoPlayer] seeking 事件，当前时间:', video.currentTime);
    };
    const handleSeeked = () => {
      console.log('[VideoPlayer] seeked 事件，最终时间:', video.currentTime);
    };

    video.addEventListener('timeupdate', handleTimeUpdateEvent);
    video.addEventListener('loadedmetadata', handleLoadedMetadataEvent);
    video.addEventListener('error', handleError);
    video.addEventListener('seeking', handleSeeking);
    video.addEventListener('seeked', handleSeeked);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdateEvent);
      video.removeEventListener('loadedmetadata', handleLoadedMetadataEvent);
      video.removeEventListener('error', handleError);
      video.removeEventListener('seeking', handleSeeking);
      video.removeEventListener('seeked', handleSeeked);
    };
  }, [videoRef, onTimeUpdate, onLoadedMetadata]);

  // 当播放状态变化时控制视频
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          console.error("播放视频时出错:", error);
        });
      }
    } else {
      video.pause();
    }
  }, [isPlaying]);

  return (
    <div className="w-full h-full flex items-center justify-center relative bg-black">
      <video
        ref={videoRef}
        src={src}
        className="max-w-full max-h-full object-contain"
        onPlay={() => {}}
        onPause={() => {}}
        playsInline // 添加这个属性以支持内联播放
        preload="metadata" // 预加载元数据，减少卡顿
      />
    </div>
  );
};

export default VideoPlayer;