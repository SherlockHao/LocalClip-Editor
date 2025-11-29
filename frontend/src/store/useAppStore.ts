import { create } from 'zustand';
import type { VideoInfo, SubtitleInfo, SubtitleEntry, ExportStatus } from '@/types';

interface AppState {
  // 视频相关状态
  currentVideo: VideoInfo | null;
  videos: VideoInfo[];
  videoLoading: boolean;
  
  // 字幕相关状态
  currentSubtitle: SubtitleInfo | null;
  subtitles: SubtitleInfo[];
  subtitleEntries: SubtitleEntry[];
  subtitleLoading: boolean;
  
  // 播放器状态
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  
  // 导出状态
  exportStatus: ExportStatus | null;
  exportLoading: boolean;
  
  // UI 状态
  sidebarOpen: boolean;
  propertiesOpen: boolean;
  
  // Actions
  setCurrentVideo: (video: VideoInfo | null) => void;
  setVideos: (videos: VideoInfo[]) => void;
  setVideoLoading: (loading: boolean) => void;
  
  setCurrentSubtitle: (subtitle: SubtitleInfo | null) => void;
  setSubtitles: (subtitles: SubtitleInfo[]) => void;
  setSubtitleEntries: (entries: SubtitleEntry[]) => void;
  setSubtitleLoading: (loading: boolean) => void;
  
  setPlaying: (playing: boolean) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setVolume: (volume: number) => void;
  
  setExportStatus: (status: ExportStatus | null) => void;
  setExportLoading: (loading: boolean) => void;
  
  setSidebarOpen: (open: boolean) => void;
  setPropertiesOpen: (open: boolean) => void;
  
  // 重置状态
  reset: () => void;
}

const initialState = {
  currentVideo: null,
  videos: [],
  videoLoading: false,
  
  currentSubtitle: null,
  subtitles: [],
  subtitleEntries: [],
  subtitleLoading: false,
  
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  
  exportStatus: null,
  exportLoading: false,
  
  sidebarOpen: true,
  propertiesOpen: true,
};

export const useAppStore = create<AppState>((set, get) => ({
  ...initialState,
  
  setCurrentVideo: (video) => set({ currentVideo: video }),
  setVideos: (videos) => set({ videos }),
  setVideoLoading: (loading) => set({ videoLoading: loading }),
  
  setCurrentSubtitle: (subtitle) => set({ currentSubtitle: subtitle }),
  setSubtitles: (subtitles) => set({ subtitles }),
  setSubtitleEntries: (entries) => set({ subtitleEntries: entries }),
  setSubtitleLoading: (loading) => set({ subtitleLoading: loading }),
  
  setPlaying: (playing) => set({ isPlaying: playing }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setVolume: (volume) => set({ volume }),
  
  setExportStatus: (status) => set({ exportStatus: status }),
  setExportLoading: (loading) => set({ exportLoading: loading }),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setPropertiesOpen: (open) => set({ propertiesOpen: open }),
  
  reset: () => set(initialState),
}));

// 选择器 hooks
export const useVideoState = () => {
  const store = useAppStore();
  return {
    currentVideo: store.currentVideo,
    videos: store.videos,
    videoLoading: store.videoLoading,
    setCurrentVideo: store.setCurrentVideo,
    setVideos: store.setVideos,
    setVideoLoading: store.setVideoLoading,
  };
};

export const useSubtitleState = () => {
  const store = useAppStore();
  return {
    currentSubtitle: store.currentSubtitle,
    subtitles: store.subtitles,
    subtitleEntries: store.subtitleEntries,
    subtitleLoading: store.subtitleLoading,
    setCurrentSubtitle: store.setCurrentSubtitle,
    setSubtitles: store.setSubtitles,
    setSubtitleEntries: store.setSubtitleEntries,
    setSubtitleLoading: store.setSubtitleLoading,
  };
};

export const usePlayerState = () => {
  const store = useAppStore();
  return {
    isPlaying: store.isPlaying,
    currentTime: store.currentTime,
    duration: store.duration,
    volume: store.volume,
    setPlaying: store.setPlaying,
    setCurrentTime: store.setCurrentTime,
    setDuration: store.setDuration,
    setVolume: store.setVolume,
  };
};

export const useExportState = () => {
  const store = useAppStore();
  return {
    exportStatus: store.exportStatus,
    exportLoading: store.exportLoading,
    setExportStatus: store.setExportStatus,
    setExportLoading: store.setExportLoading,
  };
};

export const useUIState = () => {
  const store = useAppStore();
  return {
    sidebarOpen: store.sidebarOpen,
    propertiesOpen: store.propertiesOpen,
    setSidebarOpen: store.setSidebarOpen,
    setPropertiesOpen: store.setPropertiesOpen,
  };
};