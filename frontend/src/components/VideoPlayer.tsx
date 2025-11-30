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

    video.addEventListener('timeupdate', handleTimeUpdateEvent);
    video.addEventListener('loadedmetadata', handleLoadedMetadataEvent);
    video.addEventListener('error', handleError);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdateEvent);
      video.removeEventListener('loadedmetadata', handleLoadedMetadataEvent);
      video.removeEventListener('error', handleError);
    };
  }, [videoRef, onTimeUpdate, onLoadedMetadata]);

  // 当播放状态变化时控制视频 - 使用useCallback优化
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

  // 优化时间更新处理，减少不必要的更新
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !hasLoaded || Math.abs(video.currentTime - currentTime) < 0.1) return;

    // 只在需要时更新时间，减少卡顿
    const timer = setTimeout(() => {
      video.currentTime = currentTime;
    }, 0);

    return () => clearTimeout(timer);
  }, [currentTime, hasLoaded]);

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