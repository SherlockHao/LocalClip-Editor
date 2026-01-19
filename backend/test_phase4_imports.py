# -*- coding: utf-8 -*-
"""
测试 Phase 4 新模块的导入
"""

print("=" * 60)
print("测试 Phase 4 模块导入")
print("=" * 60)

# 测试 1: 导入 progress_manager
try:
    from progress_manager import update_task_progress, mark_task_completed
    print("✅ progress_manager 导入成功")
except Exception as e:
    print(f"❌ progress_manager 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 2: 导入 path_utils
try:
    from path_utils import task_path_manager
    print("✅ path_utils 导入成功")
except Exception as e:
    print(f"❌ path_utils 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 3: 导入 processing router
try:
    from routers import processing
    print("✅ routers.processing 导入成功")
except Exception as e:
    print(f"❌ routers.processing 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 测试路径管理器
try:
    paths = task_path_manager.get_task_paths("test_task_123")
    print(f"✅ 路径管理器工作正常")
    print(f"   Root: {paths['root']}")
    print(f"   Input: {paths['input']}")
    print(f"   Processed: {paths['processed']}")
    print(f"   Outputs: {paths['outputs']}")
except Exception as e:
    print(f"❌ 路径管理器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 5: 测试路由注册
try:
    from main import app
    routes = [route.path for route in app.routes]
    processing_routes = [r for r in routes if '/speaker-diarization' in r or '/translate' in r or '/voice-cloning' in r]

    if processing_routes:
        print("✅ Processing 路由已注册:")
        for route in processing_routes[:5]:  # 只显示前5个
            print(f"   - {route}")
    else:
        print("⚠️  未找到 processing 路由，可能需要重启服务")
except Exception as e:
    print(f"❌ 路由检查失败: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
print("测试完成")
print("=" * 60)
