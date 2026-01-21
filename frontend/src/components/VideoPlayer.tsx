import React, { useEffect, useState, useRef as useReactRef } from 'react';

interface Subtitle {
  start_time: number;
  end_time: number;
  speaker_id?: number;
}

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
  filteredSpeakerId?: number | null;
  subtitles?: Subtitle[];
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
  useExternalAudio = false,
  filteredSpeakerId = null,
  subtitles = []
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

    console.log('[VideoPlayer] 播放/暂停 effect 执行, isPlaying:', isPlaying);
    console.log('[VideoPlayer] video:', !!video, 'audio:', !!audio);
    console.log('[VideoPlayer] useExternalAudio:', useExternalAudio, 'audioSrc:', audioSrc);

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

        console.log('[VideoPlayer] 播放时同步音频: video.currentTime:', targetTime, 'audio.currentTime:', currentAudioTime, 'timeDiff:', timeDiff);

        // 如果时间差距很小，直接播放
        if (timeDiff < 0.1) {
          console.log('[VideoPlayer] 时间差小，直接播放音频');
          audio.play().catch(err => console.error('外部音频播放失败:', err));
        } else {
          // 否则，先设置时间，等待seeked事件后再播放
          console.log('[VideoPlayer] 时间差大，先 seek 音频到:', targetTime);
          const handleSeeked = () => {
            console.log('[VideoPlayer] 音频 seeked，开始播放');
            audio.play().catch(err => console.error('外部音频播放失败:', err));
            audio.removeEventListener('seeked', handleSeeked);
          };

          audio.addEventListener('seeked', handleSeeked);
          audio.currentTime = targetTime;
        }
      } else {
        console.log('[VideoPlayer] 不使用外部音频或条件不满足');
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

    console.log('[VideoPlayer] 同步音频 effect 执行');
    console.log('[VideoPlayer] video:', !!video, 'audio:', !!audio);
    console.log('[VideoPlayer] useExternalAudio:', useExternalAudio, 'audioSrc:', audioSrc);

    if (!video || !audio || !useExternalAudio || !audioSrc) {
      console.log('[VideoPlayer] 条件不满足，跳过音频同步设置');
      return;
    }

    const syncAudioTime = () => {
      console.log('[VideoPlayer] video seeked 事件触发');
      console.log('[VideoPlayer] video.currentTime:', video.currentTime, 'audio.currentTime:', audio.currentTime);

      const timeDiff = Math.abs(audio.currentTime - video.currentTime);
      if (timeDiff > 0.1) {
        const wasPlaying = !audio.paused;
        console.log('[VideoPlayer] 同步音频时间:', video.currentTime, 'wasPlaying:', wasPlaying);
        audio.currentTime = video.currentTime;
        // 如果音频之前在播放，确保同步后继续播放
        if (wasPlaying && !video.paused) {
          audio.play().catch(err => console.error('恢复播放失败:', err));
        }
      } else {
        console.log('[VideoPlayer] 时间差小于0.1s，无需同步');
      }
    };

    console.log('[VideoPlayer] 添加 seeked 事件监听器');
    video.addEventListener('seeked', syncAudioTime);
    return () => {
      console.log('[VideoPlayer] 移除 seeked 事件监听器');
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

  // 根据筛选的说话人控制播放：跳过非筛选说话人的段落
  useEffect(() => {
    const video = videoRef.current;
    const audio = audioRef.current;

    if (!video || filteredSpeakerId === null || !subtitles.length) return;

    // 当筛选说话人改变时，立即检查并跳转
    const checkAndJumpToFilteredSpeaker = () => {
      const currentVideoTime = video.currentTime;
      const currentSubtitle = subtitles.find(
        sub => currentVideoTime >= sub.start_time && currentVideoTime <= sub.end_time
      );

      // 如果当前不是筛选的说话人，立即跳转
      if (!currentSubtitle || currentSubtitle.speaker_id !== filteredSpeakerId) {
        const nextFilteredSubtitle = subtitles.find(
          sub => sub.start_time > currentVideoTime && sub.speaker_id === filteredSpeakerId
        );

        if (nextFilteredSubtitle) {
          video.currentTime = nextFilteredSubtitle.start_time;
          if (audio && useExternalAudio) {
            audio.currentTime = nextFilteredSubtitle.start_time;
          }
        } else {
          // 查找第一个筛选说话人的段落
          const firstFilteredSubtitle = subtitles.find(
            sub => sub.speaker_id === filteredSpeakerId
          );
          if (firstFilteredSubtitle) {
            video.currentTime = firstFilteredSubtitle.start_time;
            if (audio && useExternalAudio) {
              audio.currentTime = firstFilteredSubtitle.start_time;
            }
          } else {
            // 没有任何筛选说话人的段落，暂停
            video.pause();
            if (audio && useExternalAudio) {
              audio.pause();
            }
          }
        }
      }
    };

    // 筛选说话人改变时立即检查
    checkAndJumpToFilteredSpeaker();

    const handleTimeUpdate = () => {
      const currentVideoTime = video.currentTime;

      // 查找当前时间对应的字幕
      const currentSubtitle = subtitles.find(
        sub => currentVideoTime >= sub.start_time && currentVideoTime <= sub.end_time
      );

      // 如果当前在某个字幕段落中
      if (currentSubtitle) {
        // 如果不是筛选的说话人，跳到下一个筛选说话人的段落
        if (currentSubtitle.speaker_id !== filteredSpeakerId) {
          // 查找下一个筛选说话人的段落
          const nextFilteredSubtitle = subtitles.find(
            sub => sub.start_time > currentVideoTime && sub.speaker_id === filteredSpeakerId
          );

          if (nextFilteredSubtitle) {
            // 跳转到下一个筛选说话人的段落开始
            video.currentTime = nextFilteredSubtitle.start_time;
            if (audio && useExternalAudio) {
              audio.currentTime = nextFilteredSubtitle.start_time;
            }
          } else {
            // 没有下一个筛选说话人的段落了，暂停播放
            video.pause();
            if (audio && useExternalAudio) {
              audio.pause();
            }
          }
        }
      } else {
        // 不在任何字幕段落中，查找下一个筛选说话人的段落
        const nextFilteredSubtitle = subtitles.find(
          sub => sub.start_time > currentVideoTime && sub.speaker_id === filteredSpeakerId
        );

        if (nextFilteredSubtitle) {
          video.currentTime = nextFilteredSubtitle.start_time;
          if (audio && useExternalAudio) {
            audio.currentTime = nextFilteredSubtitle.start_time;
          }
        } else {
          // 没有下一个段落了，暂停
          video.pause();
          if (audio && useExternalAudio) {
            audio.pause();
          }
        }
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [filteredSpeakerId, subtitles, useExternalAudio]);

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