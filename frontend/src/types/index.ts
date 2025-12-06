// 通用类型定义
export interface VideoInfo {
  filename: string;
  filepath: string;
  size: number;
  duration: number;
  width: number;
  height: number;
  fps: number;
  codec: string;
  bitrate?: number;
}

export interface SubtitleInfo {
  filename: string;
  filepath: string;
  entries_count: number;
  total_duration: number;
  entries?: SubtitleEntry[];
}

export interface SubtitleEntry {
  index: number;
  start_time: number;
  end_time: number;
  duration: number;
  text: string;
  start_formatted: string;
  end_formatted: string;
  left_percent?: number;
  width_percent?: number;
  speaker_id?: number;  // 新增：说话人ID
  target_text?: string;  // 新增：目标语言文本
  cloned_audio_path?: string;  // 新增：克隆音频路径
  cloned_speaker_id?: number;  // 新增：克隆时使用的说话人ID
}

export interface ExportRequest {
  video_path: string;
  subtitle_path?: string;
  output_filename: string;
  resolution?: [number, number];
  bitrate?: string;
  hardware_acceleration: boolean;
}

export interface ExportStatus {
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  output_path?: string;
  result?: any;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// API 响应类型
export interface UploadVideoResponse {
  success: boolean;
  file_info: {
    filename: string;
    filepath: string;
    size: number;
    modified: number;
  };
  video_info: {
    duration: number;
    width: number;
    height: number;
    fps: number;
    codec: string;
    size: number;
    bitrate: number;
  };
}

export interface UploadSubtitleResponse {
  success: boolean;
  file_info: {
    filename: string;
    filepath: string;
    size: number;
    modified: number;
  };
  subtitle_info: {
    entries_count: number;
    total_duration: number;
    entries: SubtitleEntry[];
  };
}