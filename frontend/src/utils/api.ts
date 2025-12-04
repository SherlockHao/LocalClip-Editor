import axios from 'axios';
import type { 
  VideoInfo, 
  SubtitleInfo, 
  ExportRequest, 
  ExportStatus,
  UploadVideoResponse,
  UploadSubtitleResponse,
  ApiResponse 
} from '@/types';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const errorMessage = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(errorMessage));
  }
);

export class ApiClient {
  // 健康检查
  static async healthCheck(): Promise<any> {
    return apiClient.get('/health');
  }

  // 上传视频
  static async uploadVideo(file: File): Promise<UploadVideoResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiClient.post('/upload/video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // 上传字幕
  static async uploadSubtitle(file: File): Promise<UploadSubtitleResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiClient.post('/upload/subtitle', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // 获取视频列表
  static async getVideos(): Promise<{ success: boolean; videos: VideoInfo[] }> {
    return apiClient.get('/videos');
  }

  // 获取字幕列表
  static async getSubtitles(): Promise<{ success: boolean; subtitles: SubtitleInfo[] }> {
    return apiClient.get('/subtitles');
  }

  // 获取视频详细信息
  static async getVideoInfo(filename: string): Promise<{ success: boolean; video_info: any }> {
    return apiClient.get(`/video/info/${filename}`);
  }

  // 获取字幕时间轴数据
  static async getSubtitleTimeline(filename: string, videoDuration: number): Promise<{
    success: boolean;
    timeline_data: any[];
    total_entries: number;
  }> {
    return apiClient.get(`/subtitle/timeline/${filename}?video_duration=${videoDuration}`);
  }

  // 导出视频
  static async exportVideo(request: ExportRequest): Promise<{ success: boolean; task_id: string; message: string }> {
    return apiClient.post('/export', request);
  }

  // 获取导出状态
  static async getExportStatus(taskId: string): Promise<ExportStatus> {
    return apiClient.get(`/export/status/${taskId}`);
  }

  // 下载文件
  static async downloadFile(filename: string): Promise<Blob> {
    const response = await apiClient.get(`/download/${filename}`, {
      responseType: 'blob',
    });
    return response;
  }

  // 删除文件
  static async deleteFile(filename: string): Promise<{ success: boolean; message: string }> {
    return apiClient.delete(`/files/${filename}`);
  }
}

// 文件上传辅助函数
export const uploadWithProgress = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient.post('/upload/video', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });
};

// 格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化时间
export const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};