/**
 * 前端内存泄漏检测工具
 *
 * 用于检测 React 应用中的内存泄漏问题
 *
 * 使用方法 (在浏览器控制台中):
 * 1. import { memoryLeakDetector } from './utils/memoryLeakDetector'
 * 2. memoryLeakDetector.startMonitoring()
 * 3. 执行操作 (切换页面、执行任务等)
 * 4. memoryLeakDetector.stopMonitoring()
 * 5. memoryLeakDetector.analyze()
 */

interface MemorySample {
  timestamp: number;
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

interface TimerInfo {
  type: 'interval' | 'timeout';
  id: number;
  timestamp: number;
  stack?: string;
}

interface ListenerInfo {
  target: string;
  type: string;
  timestamp: number;
  stack?: string;
}

class MemoryLeakDetector {
  private samples: MemorySample[] = [];
  private monitoring: boolean = false;
  private intervalId: number | null = null;

  // 跟踪定时器
  private activeTimers: Map<number, TimerInfo> = new Map();
  private activeIntervals: Map<number, TimerInfo> = new Map();

  // 跟踪事件监听器 (简化版)
  private listenerCount: number = 0;

  constructor() {
    this.patchTimers();
  }

  /**
   * 开始内存监控
   */
  startMonitoring(intervalMs: number = 2000): void {
    if (this.monitoring) {
      console.warn('[MemoryLeakDetector] 已在监控中');
      return;
    }

    this.monitoring = true;
    this.samples = [];

    console.log('[MemoryLeakDetector] 开始监控内存...');
    console.log('[MemoryLeakDetector] 提示: 执行操作后调用 stopMonitoring() 和 analyze()');

    this.takeSample();

    this.intervalId = window.setInterval(() => {
      this.takeSample();
    }, intervalMs);
  }

  /**
   * 停止内存监控
   */
  stopMonitoring(): void {
    if (!this.monitoring) {
      console.warn('[MemoryLeakDetector] 未在监控中');
      return;
    }

    this.monitoring = false;

    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }

    console.log(`[MemoryLeakDetector] 监控已停止，共采集 ${this.samples.length} 个样本`);
  }

  /**
   * 采集内存样本
   */
  private takeSample(): void {
    // @ts-ignore - performance.memory 是非标准 API
    const memory = (performance as any).memory;

    if (!memory) {
      console.warn('[MemoryLeakDetector] 此浏览器不支持 performance.memory API');
      console.warn('[MemoryLeakDetector] 请使用 Chrome 并启用 --enable-precise-memory-info 标志');
      return;
    }

    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: memory.usedJSHeapSize,
      totalJSHeapSize: memory.totalJSHeapSize,
      jsHeapSizeLimit: memory.jsHeapSizeLimit,
    };

    this.samples.push(sample);
  }

  /**
   * 分析内存使用情况
   */
  analyze(): void {
    if (this.samples.length < 2) {
      console.warn('[MemoryLeakDetector] 样本数量不足，无法分析');
      return;
    }

    const toMB = (bytes: number) => (bytes / 1024 / 1024).toFixed(2);

    const first = this.samples[0];
    const last = this.samples[this.samples.length - 1];
    const usedHeaps = this.samples.map((s) => s.usedJSHeapSize);
    const minHeap = Math.min(...usedHeaps);
    const maxHeap = Math.max(...usedHeaps);
    const avgHeap = usedHeaps.reduce((a, b) => a + b, 0) / usedHeaps.length;

    const heapDiff = last.usedJSHeapSize - first.usedJSHeapSize;
    const durationMs = last.timestamp - first.timestamp;

    console.log('\n========================================');
    console.log('内存泄漏分析报告');
    console.log('========================================\n');

    console.log('【内存使用统计】');
    console.log(`  采样数量: ${this.samples.length}`);
    console.log(`  监控时长: ${(durationMs / 1000).toFixed(1)} 秒`);
    console.log(`  起始内存: ${toMB(first.usedJSHeapSize)} MB`);
    console.log(`  结束内存: ${toMB(last.usedJSHeapSize)} MB`);
    console.log(`  最小内存: ${toMB(minHeap)} MB`);
    console.log(`  最大内存: ${toMB(maxHeap)} MB`);
    console.log(`  平均内存: ${toMB(avgHeap)} MB`);
    console.log(`  内存变化: ${heapDiff > 0 ? '+' : ''}${toMB(heapDiff)} MB`);

    // 判断是否有泄漏
    const leakThreshold = 10 * 1024 * 1024; // 10MB
    const hasLeak = heapDiff > leakThreshold;

    console.log('');
    if (hasLeak) {
      console.warn(`⚠️ [警告] 内存增长超过 ${toMB(leakThreshold)} MB，可能存在内存泄漏!`);
    } else {
      console.log('✅ [OK] 未检测到明显的内存泄漏');
    }

    // 分析定时器
    console.log('\n【定时器统计】');
    console.log(`  活跃 setTimeout: ${this.activeTimers.size}`);
    console.log(`  活跃 setInterval: ${this.activeIntervals.size}`);

    if (this.activeIntervals.size > 5) {
      console.warn(`⚠️ [警告] 活跃的 setInterval 数量较多，请检查是否有未清理的定时器`);
    }

    console.log('\n========================================\n');
  }

  /**
   * 获取当前活跃的定时器
   */
  getActiveTimers(): { intervals: number; timeouts: number } {
    return {
      intervals: this.activeIntervals.size,
      timeouts: this.activeTimers.size,
    };
  }

  /**
   * 强制触发垃圾回收 (需要 Chrome 开发者工具)
   */
  forceGC(): void {
    // @ts-ignore
    if (window.gc) {
      // @ts-ignore
      window.gc();
      console.log('[MemoryLeakDetector] 已触发垃圾回收');
    } else {
      console.warn('[MemoryLeakDetector] 垃圾回收不可用');
      console.warn('[MemoryLeakDetector] 请使用 Chrome 并启用 --js-flags="--expose-gc" 标志');
    }
  }

  /**
   * 补丁定时器函数以跟踪使用情况
   */
  private patchTimers(): void {
    const self = this;

    // 保存原始函数
    const originalSetTimeout = window.setTimeout;
    const originalClearTimeout = window.clearTimeout;
    const originalSetInterval = window.setInterval;
    const originalClearInterval = window.clearInterval;

    // 补丁 setTimeout
    (window as any).setTimeout = function (
      handler: TimerHandler,
      timeout?: number,
      ...args: any[]
    ): number {
      const id = originalSetTimeout.call(window, handler, timeout, ...args);
      self.activeTimers.set(id, {
        type: 'timeout',
        id,
        timestamp: Date.now(),
      });

      // 自动清理
      originalSetTimeout.call(
        window,
        () => {
          self.activeTimers.delete(id);
        },
        (timeout || 0) + 100
      );

      return id;
    };

    // 补丁 clearTimeout
    (window as any).clearTimeout = function (id?: number): void {
      if (id !== undefined) {
        self.activeTimers.delete(id);
      }
      return originalClearTimeout.call(window, id);
    };

    // 补丁 setInterval
    (window as any).setInterval = function (
      handler: TimerHandler,
      timeout?: number,
      ...args: any[]
    ): number {
      const id = originalSetInterval.call(window, handler, timeout, ...args);
      self.activeIntervals.set(id, {
        type: 'interval',
        id,
        timestamp: Date.now(),
      });
      return id;
    };

    // 补丁 clearInterval
    (window as any).clearInterval = function (id?: number): void {
      if (id !== undefined) {
        self.activeIntervals.delete(id);
      }
      return originalClearInterval.call(window, id);
    };
  }

  /**
   * 打印内存使用曲线 (简单文本版)
   */
  printMemoryChart(): void {
    if (this.samples.length < 2) {
      console.warn('[MemoryLeakDetector] 样本数量不足');
      return;
    }

    const toMB = (bytes: number) => bytes / 1024 / 1024;
    const heaps = this.samples.map((s) => toMB(s.usedJSHeapSize));
    const min = Math.min(...heaps);
    const max = Math.max(...heaps);
    const range = max - min || 1;

    console.log('\n内存使用曲线:');
    console.log(`${max.toFixed(1)} MB ┤`);

    // 简化为10行
    const rows = 10;
    const cols = Math.min(50, this.samples.length);
    const step = Math.max(1, Math.floor(this.samples.length / cols));

    for (let row = rows - 1; row >= 0; row--) {
      const threshold = min + (range * (row + 0.5)) / rows;
      let line = '         │';

      for (let col = 0; col < cols; col++) {
        const idx = col * step;
        if (idx < heaps.length) {
          line += heaps[idx] >= threshold ? '█' : ' ';
        }
      }

      if (row === rows - 1) {
        console.log(`${max.toFixed(1)} MB ┤${line.slice(10)}`);
      } else if (row === 0) {
        console.log(`${min.toFixed(1)} MB ┤${line.slice(10)}`);
      } else {
        console.log(`         │${line.slice(10)}`);
      }
    }

    console.log('         └' + '─'.repeat(cols));
    console.log(`          0${' '.repeat(cols - 10)}${this.samples.length} samples`);
  }
}

// 导出单例
export const memoryLeakDetector = new MemoryLeakDetector();

// 添加到全局对象以便在控制台使用
if (typeof window !== 'undefined') {
  (window as any).memoryLeakDetector = memoryLeakDetector;
}

export default memoryLeakDetector;
