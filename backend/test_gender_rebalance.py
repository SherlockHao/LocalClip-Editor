"""
性别重平衡逻辑自测脚本
独立测试 rebalance_genders 方法的各种场景（不需要加载模型）
"""

from typing import Dict


def rebalance_genders(
    gender_results: Dict[int, str],
    prob_results: Dict[int, Dict[str, float]]
) -> Dict[int, str]:
    """
    根据概率重新平衡性别分配，处理异常的性别分布
    （复制自 gender_classifier.py 用于独立测试）
    """
    total_speakers = len(gender_results)
    result = gender_results.copy()

    if total_speakers < 4:
        print(f"\n[性别重平衡] 说话人数量({total_speakers}) < 4，无需重平衡")
        return result

    def count_genders():
        males = [sid for sid, g in result.items() if g == "male"]
        females = [sid for sid, g in result.items() if g == "female"]
        return males, females

    males, females = count_genders()
    male_count, female_count = len(males), len(females)

    print(f"\n[性别重平衡] 检查性别分布: {male_count}男 {female_count}女 (共{total_speakers}人)")

    # Case 1: ≥4个说话人，全部同性
    if total_speakers >= 4 and (male_count == 0 or female_count == 0):
        if male_count == 0:
            best = max(females, key=lambda sid: prob_results[sid]["male"])
            result[best] = "male"
            print(f"[性别重平衡] Case1触发: 全为女性({female_count}人)")
            print(f"  → 将说话人 {best} 改为男性 (male_prob: {prob_results[best]['male']:.3f})")
        else:
            best = max(males, key=lambda sid: prob_results[sid]["female"])
            result[best] = "female"
            print(f"[性别重平衡] Case1触发: 全为男性({male_count}人)")
            print(f"  → 将说话人 {best} 改为女性 (female_prob: {prob_results[best]['female']:.3f})")

        males, females = count_genders()
        male_count, female_count = len(males), len(females)
        print(f"[性别重平衡] Case1后分布: {male_count}男 {female_count}女")

    # Case 2: ≥5个说话人，只有≤1个少数性别
    if total_speakers >= 5:
        minority_count = min(male_count, female_count)

        if minority_count <= 1:
            if male_count > female_count:
                best = max(males, key=lambda sid: prob_results[sid]["female"])
                result[best] = "female"
                print(f"[性别重平衡] Case2触发: {male_count}男{female_count}女，少数性别≤1")
                print(f"  → 将说话人 {best} 改为女性 (female_prob: {prob_results[best]['female']:.3f})")
            else:
                best = max(females, key=lambda sid: prob_results[sid]["male"])
                result[best] = "male"
                print(f"[性别重平衡] Case2触发: {male_count}男{female_count}女，少数性别≤1")
                print(f"  → 将说话人 {best} 改为男性 (male_prob: {prob_results[best]['male']:.3f})")

            males, females = count_genders()
            print(f"[性别重平衡] Case2后分布: {len(males)}男 {len(females)}女")
        else:
            print(f"[性别重平衡] Case2未触发: 少数性别数量({minority_count}) > 1，分布正常")
    elif total_speakers >= 4:
        print(f"[性别重平衡] Case2未触发: 说话人数量({total_speakers}) < 5")

    return result


def test_rebalance_genders():
    """测试性别重平衡逻辑"""

    print("=" * 60)
    print("性别重平衡逻辑自测")
    print("=" * 60)

    all_passed = True

    # ==================== 测试用例 ====================

    # Case 1: 3个说话人，不触发任何重平衡（< 4人）
    print("\n" + "-" * 50)
    print("测试1: 3个说话人全男（< 4人，不触发）")
    gender_results = {0: "male", 1: "male", 2: "male"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.8, "female": 0.2},
        2: {"male": 0.7, "female": 0.3},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "male", 2: "male"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 2: 4个说话人全男 → 触发Case1，female_prob最高的改为女
    print("\n" + "-" * 50)
    print("测试2: 4个说话人全男（触发Case1）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "male"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.6, "female": 0.4},  # female_prob最高
        2: {"male": 0.8, "female": 0.2},
        3: {"male": 0.7, "female": 0.3},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "female", 2: "male", 3: "male"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 3: 4个说话人全女 → 触发Case1，male_prob最高的改为男
    print("\n" + "-" * 50)
    print("测试3: 4个说话人全女（触发Case1）")
    gender_results = {0: "female", 1: "female", 2: "female", 3: "female"}
    prob_results = {
        0: {"male": 0.3, "female": 0.7},
        1: {"male": 0.2, "female": 0.8},
        2: {"male": 0.45, "female": 0.55},  # male_prob最高
        3: {"male": 0.1, "female": 0.9},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "female", 1: "female", 2: "male", 3: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 4: 4个说话人，3男1女 → 不触发（有异性，且 < 5人）
    print("\n" + "-" * 50)
    print("测试4: 4个说话人，3男1女（不触发）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "female"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.6, "female": 0.4},
        2: {"male": 0.8, "female": 0.2},
        3: {"male": 0.3, "female": 0.7},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "male", 2: "male", 3: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 5: 5个说话人全男 → 触发Case1 + Case2，最终3男2女
    print("\n" + "-" * 50)
    print("测试5: 5个说话人全男（触发Case1 + Case2）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "male", 4: "male"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.55, "female": 0.45},  # female_prob第一高
        2: {"male": 0.6, "female": 0.4},    # female_prob第二高
        3: {"male": 0.8, "female": 0.2},
        4: {"male": 0.7, "female": 0.3},
    }
    result = rebalance_genders(gender_results, prob_results)
    # Case1: speaker 1 改为女 → 4男1女
    # Case2: 在剩余4男中找female_prob最高的(speaker 2)改为女 → 3男2女
    expected = {0: "male", 1: "female", 2: "female", 3: "male", 4: "male"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 6: 5个说话人，4男1女 → 触发Case2，最终3男2女
    print("\n" + "-" * 50)
    print("测试6: 5个说话人，4男1女（触发Case2）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "male", 4: "female"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.55, "female": 0.45},  # 男性中female_prob最高
        2: {"male": 0.7, "female": 0.3},
        3: {"male": 0.8, "female": 0.2},
        4: {"male": 0.3, "female": 0.7},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "female", 2: "male", 3: "male", 4: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 7: 5个说话人，1男4女 → 触发Case2，最终2男3女
    print("\n" + "-" * 50)
    print("测试7: 5个说话人，1男4女（触发Case2）")
    gender_results = {0: "male", 1: "female", 2: "female", 3: "female", 4: "female"}
    prob_results = {
        0: {"male": 0.8, "female": 0.2},
        1: {"male": 0.4, "female": 0.6},    # 女性中male_prob最高
        2: {"male": 0.2, "female": 0.8},
        3: {"male": 0.1, "female": 0.9},
        4: {"male": 0.3, "female": 0.7},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "male", 2: "female", 3: "female", 4: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 8: 5个说话人，3男2女 → 不触发（分布正常）
    print("\n" + "-" * 50)
    print("测试8: 5个说话人，3男2女（不触发）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "female", 4: "female"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.8, "female": 0.2},
        2: {"male": 0.7, "female": 0.3},
        3: {"male": 0.3, "female": 0.7},
        4: {"male": 0.2, "female": 0.8},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "male", 2: "male", 3: "female", 4: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 9: 6个说话人，5男1女 → 触发Case2，最终4男2女
    print("\n" + "-" * 50)
    print("测试9: 6个说话人，5男1女（触发Case2）")
    gender_results = {0: "male", 1: "male", 2: "male", 3: "male", 4: "male", 5: "female"}
    prob_results = {
        0: {"male": 0.9, "female": 0.1},
        1: {"male": 0.55, "female": 0.45},  # 男性中female_prob最高
        2: {"male": 0.7, "female": 0.3},
        3: {"male": 0.8, "female": 0.2},
        4: {"male": 0.75, "female": 0.25},
        5: {"male": 0.3, "female": 0.7},
    }
    result = rebalance_genders(gender_results, prob_results)
    expected = {0: "male", 1: "female", 2: "male", 3: "male", 4: "male", 5: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # Case 10: 6个说话人全女 → 触发Case1 + Case2，最终2男4女
    print("\n" + "-" * 50)
    print("测试10: 6个说话人全女（触发Case1 + Case2）")
    gender_results = {0: "female", 1: "female", 2: "female", 3: "female", 4: "female", 5: "female"}
    prob_results = {
        0: {"male": 0.48, "female": 0.52},  # male_prob第一高
        1: {"male": 0.45, "female": 0.55},  # male_prob第二高
        2: {"male": 0.2, "female": 0.8},
        3: {"male": 0.1, "female": 0.9},
        4: {"male": 0.3, "female": 0.7},
        5: {"male": 0.15, "female": 0.85},
    }
    result = rebalance_genders(gender_results, prob_results)
    # Case1: speaker 0 改为男 → 1男5女
    # Case2: 在剩余5女中找male_prob最高的(speaker 1)改为男 → 2男4女
    expected = {0: "male", 1: "male", 2: "female", 3: "female", 4: "female", 5: "female"}
    passed = result == expected
    print(f"结果: {result}")
    print(f"期望: {expected}")
    print(f"通过: {'PASS' if passed else 'FAIL'}")
    all_passed = all_passed and passed

    # ==================== 总结 ====================
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    import sys
    success = test_rebalance_genders()
    sys.exit(0 if success else 1)
