import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface ProgressUpdate {
  type: string;
  language: string;
  stage: string;
  progress: number;
  message: string;
}

interface TaskProgress {
  [language: string]: {
    [stage: string]: {
      progress: number;
      message: string;
    };
  };
}

export const useTaskProgress = (taskId: string) => {
  const [progress, setProgress] = useState<TaskProgress>({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 尝试 WebSocket 连接
    connectWebSocket();

    // 启动轮询作为备份
    startPolling();

    return () => {
      // 清理 WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // 清理轮询
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }

      // 清理重连定时器
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [taskId]);

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const ws = new WebSocket(`${protocol}//${host}/ws/tasks/${taskId}`);

      ws.onopen = () => {
        console.log('[WebSocket] 连接成功');
        setIsConnected(true);

        // WebSocket 连接成功，停止轮询
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data: ProgressUpdate = JSON.parse(event.data);
          updateProgress(data);
        } catch (error) {
          console.error('[WebSocket] 解析消息失败:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] 错误:', error);
      };

      ws.onclose = () => {
        console.log('[WebSocket] 连接关闭');
        setIsConnected(false);
        wsRef.current = null;

        // WebSocket 断开，恢复轮询
        startPolling();

        // 5秒后尝试重连
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WebSocket] 尝试重连...');
          connectWebSocket();
        }, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] 连接失败:', error);
      startPolling();
    }
  };

  const startPolling = () => {
    if (pollingRef.current) return; // 已经在轮询

    console.log('[轮询] 启动轮询');
    pollingRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`/api/tasks/${taskId}`);
        setProgress(response.data.language_status || {});
      } catch (error) {
        console.error('[轮询] 获取任务状态失败:', error);
      }
    }, 2000); // 每2秒轮询一次
  };

  const updateProgress = (data: ProgressUpdate) => {
    setProgress((prev) => ({
      ...prev,
      [data.language]: {
        ...prev[data.language],
        [data.stage]: {
          progress: data.progress,
          message: data.message
        }
      }
    }));
  };

  return { progress, isConnected };
};
