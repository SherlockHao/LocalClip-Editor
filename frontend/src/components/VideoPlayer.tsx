import React, { useEffect, useState } from 'react';

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

  // 当前时间变化时更新视频时间
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !hasLoaded) return; // 确保视频已加载后再设置时间

    video.currentTime = currentTime;
  }, [currentTime, hasLoaded]);

  return (
    <div className="w-full h-full flex items-center justify-center relative">
      <video
        ref={videoRef}
        src={src}
        className="max-w-full max-h-full object-contain"
        onPlay={() => {}}
        onPause={() => {}}
        playsInline // 添加这个属性以支持内联播放
      />
    </div>
  );
};

export default VideoPlayer;