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

  // 仅在视频加载完成且视频时间与状态时间差异较大时更新视频时间
  // 避免频繁更新导致性能问题或跳转冲突
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !hasLoaded) return;

    // 只有当时间差异较大时才更新（>1秒），避免频繁同步导致跳转问题
    if (Math.abs(video.currentTime - currentTime) > 1.0) {
      video.currentTime = currentTime;
    }
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