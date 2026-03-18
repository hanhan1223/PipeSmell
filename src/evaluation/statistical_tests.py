"""
统计显著性检验模块

提供多种统计检验方法，用于验证方法间的性能差异是否显著。
"""

from typing import List, Tuple, Dict
import numpy as np
from scipy import stats


class StatisticalTests:
    """统计检验工具类
    
    提供配对t检验、Wilcoxon符号秩检验、效应量计算等功能。
    """
    
    @staticmethod
    def paired_t_test(method1_scores: List[float],
                     method2_scores: List[float],
                     alpha: float = 0.05) -> Dict:
        """配对t检验
        
        用于比较两个方法在相同数据集上的性能差异。
        假设：数据服从正态分布。
        
        Args:
            method1_scores: 方法1的得分列表（如F1分数）
            method2_scores: 方法2的得分列表
            alpha: 显著性水平，默认0.05
            
        Returns:
            包含t统计量、p值、是否显著等信息的字典
        """
        if len(method1_scores) != len(method2_scores):
            raise ValueError("两个方法的得分列表长度必须相同")
        
        if len(method1_scores) < 2:
            raise ValueError("至少需要2个样本")
        
        # 执行配对t检验
        t_statistic, p_value = stats.ttest_rel(method1_scores, method2_scores)
        
        # 计算均值差异
        mean_diff = np.mean(method1_scores) - np.mean(method2_scores)
        
        # 判断是否显著
        is_significant = p_value < alpha
        
        # 判断哪个方法更好
        if is_significant:
            if mean_diff > 0:
                better_method = "method1"
            else:
                better_method = "method2"
        else:
            better_method = "no_significant_difference"
        
        return {
            'test_name': 'Paired t-test',
            't_statistic': float(t_statistic),
            'p_value': float(p_value),
            'alpha': alpha,
            'is_significant': is_significant,
            'mean_difference': float(mean_diff),
            'better_method': better_method,
            'method1_mean': float(np.mean(method1_scores)),
            'method2_mean': float(np.mean(method2_scores)),
            'method1_std': float(np.std(method1_scores, ddof=1)),
            'method2_std': float(np.std(method2_scores, ddof=1))
        }
    
    @staticmethod
    def wilcoxon_test(method1_scores: List[float],
                     method2_scores: List[float],
                     alpha: float = 0.05) -> Dict:
        """Wilcoxon符号秩检验
        
        非参数检验，不假设数据服从正态分布。
        适用于样本量较小或数据不满足正态分布的情况。
        
        Args:
            method1_scores: 方法1的得分列表
            method2_scores: 方法2的得分列表
            alpha: 显著性水平，默认0.05
            
        Returns:
            包含统计量、p值、是否显著等信息的字典
        """
        if len(method1_scores) != len(method2_scores):
            raise ValueError("两个方法的得分列表长度必须相同")
        
        if len(method1_scores) < 2:
            raise ValueError("至少需要2个样本")
        
        # 执行Wilcoxon检验
        statistic, p_value = stats.wilcoxon(method1_scores, method2_scores)
        
        # 计算中位数差异
        median_diff = np.median(method1_scores) - np.median(method2_scores)
        
        # 判断是否显著
        is_significant = p_value < alpha
        
        # 判断哪个方法更好
        if is_significant:
            if median_diff > 0:
                better_method = "method1"
            else:
                better_method = "method2"
        else:
            better_method = "no_significant_difference"
        
        return {
            'test_name': 'Wilcoxon signed-rank test',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': alpha,
            'is_significant': is_significant,
            'median_difference': float(median_diff),
            'better_method': better_method,
            'method1_median': float(np.median(method1_scores)),
            'method2_median': float(np.median(method2_scores))
        }
    
    @staticmethod
    def cohen_d(method1_scores: List[float],
               method2_scores: List[float]) -> float:
        """计算Cohen's d效应量
        
        衡量两个方法之间差异的大小。
        - |d| < 0.2: 小效应
        - 0.2 <= |d| < 0.5: 中等效应
        - 0.5 <= |d| < 0.8: 大效应
        - |d| >= 0.8: 非常大效应
        
        Args:
            method1_scores: 方法1的得分列表
            method2_scores: 方法2的得分列表
            
        Returns:
            Cohen's d值
        """
        mean1 = np.mean(method1_scores)
        mean2 = np.mean(method2_scores)
        
        std1 = np.std(method1_scores, ddof=1)
        std2 = np.std(method2_scores, ddof=1)
        
        n1 = len(method1_scores)
        n2 = len(method2_scores)
        
        # 计算合并标准差
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        d = (mean1 - mean2) / pooled_std
        
        return float(d)
    
    @staticmethod
    def interpret_effect_size(d: float) -> str:
        """解释效应量大小
        
        Args:
            d: Cohen's d值
            
        Returns:
            效应量解释字符串
        """
        abs_d = abs(d)
        
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"
    
    @staticmethod
    def friedman_test(*method_scores: List[float], alpha: float = 0.05) -> Dict:
        """Friedman检验（多方法比较）
        
        非参数检验，用于比较3个或更多方法。
        
        Args:
            *method_scores: 多个方法的得分列表
            alpha: 显著性水平
            
        Returns:
            包含统计量、p值、是否显著等信息的字典
        """
        if len(method_scores) < 3:
            raise ValueError("Friedman检验至少需要3个方法")
        
        # 检查所有列表长度是否相同
        lengths = [len(scores) for scores in method_scores]
        if len(set(lengths)) > 1:
            raise ValueError("所有方法的得分列表长度必须相同")
        
        # 执行Friedman检验
        statistic, p_value = stats.friedmanchisquare(*method_scores)
        
        is_significant = p_value < alpha
        
        return {
            'test_name': 'Friedman test',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': alpha,
            'is_significant': is_significant,
            'num_methods': len(method_scores),
            'num_samples': lengths[0]
        }
    
    @staticmethod
    def nemenyi_post_hoc(method_scores: Dict[str, List[float]],
                        alpha: float = 0.05) -> Dict[Tuple[str, str], Dict]:
        """Nemenyi事后检验（Friedman检验后的成对比较）
        
        Args:
            method_scores: 方法名到得分列表的字典
            alpha: 显著性水平
            
        Returns:
            成对比较结果字典
        """
        from scipy.stats import rankdata
        
        method_names = list(method_scores.keys())
        num_methods = len(method_names)
        num_samples = len(method_scores[method_names[0]])
        
        # 计算平均秩
        ranks = {name: [] for name in method_names}
        
        for i in range(num_samples):
            sample_scores = [method_scores[name][i] for name in method_names]
            sample_ranks = rankdata(sample_scores, method='average')
            
            for j, name in enumerate(method_names):
                ranks[name].append(sample_ranks[j])
        
        avg_ranks = {name: np.mean(ranks[name]) for name in method_names}
        
        # 计算临界差异（Critical Difference）
        q_alpha = 2.394  # 对于alpha=0.05, k=4的近似值（需要查表）
        cd = q_alpha * np.sqrt((num_methods * (num_methods + 1)) / (6 * num_samples))
        
        # 成对比较
        comparisons = {}
        
        for i in range(num_methods):
            for j in range(i + 1, num_methods):
                name1 = method_names[i]
                name2 = method_names[j]
                
                rank_diff = abs(avg_ranks[name1] - avg_ranks[name2])
                is_significant = rank_diff > cd
                
                comparisons[(name1, name2)] = {
                    'rank_difference': float(rank_diff),
                    'critical_difference': float(cd),
                    'is_significant': is_significant,
                    'avg_rank_method1': float(avg_ranks[name1]),
                    'avg_rank_method2': float(avg_ranks[name2])
                }
        
        return comparisons
    
    @staticmethod
    def bootstrap_confidence_interval(scores: List[float],
                                     confidence_level: float = 0.95,
                                     num_bootstrap: int = 10000) -> Tuple[float, float]:
        """Bootstrap置信区间估计
        
        Args:
            scores: 得分列表
            confidence_level: 置信水平，默认0.95
            num_bootstrap: Bootstrap采样次数
            
        Returns:
            (下界, 上界)元组
        """
        bootstrap_means = []
        
        for _ in range(num_bootstrap):
            # 有放回抽样
            sample = np.random.choice(scores, size=len(scores), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        # 计算置信区间
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = np.percentile(bootstrap_means, lower_percentile)
        upper_bound = np.percentile(bootstrap_means, upper_percentile)
        
        return float(lower_bound), float(upper_bound)


class MultiMethodComparison:
    """多方法比较工具
    
    提供完整的多方法统计比较流程。
    """
    
    def __init__(self, alpha: float = 0.05):
        """初始化
        
        Args:
            alpha: 显著性水平
        """
        self.alpha = alpha
    
    def compare_all(self, method_scores: Dict[str, List[float]]) -> Dict:
        """比较所有方法
        
        Args:
            method_scores: 方法名到得分列表的字典
            
        Returns:
            完整的比较结果
        """
        results = {
            'num_methods': len(method_scores),
            'num_samples': len(list(method_scores.values())[0]),
            'descriptive_statistics': {},
            'pairwise_comparisons': {},
            'overall_test': None
        }
        
        # 1. 描述性统计
        for method_name, scores in method_scores.items():
            results['descriptive_statistics'][method_name] = {
                'mean': float(np.mean(scores)),
                'median': float(np.median(scores)),
                'std': float(np.std(scores, ddof=1)),
                'min': float(np.min(scores)),
                'max': float(np.max(scores)),
                'ci_95': StatisticalTests.bootstrap_confidence_interval(scores)
            }
        
        # 2. 总体检验（Friedman）
        if len(method_scores) >= 3:
            results['overall_test'] = StatisticalTests.friedman_test(
                *method_scores.values(), alpha=self.alpha
            )
        
        # 3. 成对比较
        method_names = list(method_scores.keys())
        
        for i in range(len(method_names)):
            for j in range(i + 1, len(method_names)):
                name1 = method_names[i]
                name2 = method_names[j]
                
                scores1 = method_scores[name1]
                scores2 = method_scores[name2]
                
                # t检验
                t_test_result = StatisticalTests.paired_t_test(
                    scores1, scores2, self.alpha
                )
                
                # Wilcoxon检验
                wilcoxon_result = StatisticalTests.wilcoxon_test(
                    scores1, scores2, self.alpha
                )
                
                # 效应量
                effect_size = StatisticalTests.cohen_d(scores1, scores2)
                
                results['pairwise_comparisons'][f"{name1}_vs_{name2}"] = {
                    't_test': t_test_result,
                    'wilcoxon_test': wilcoxon_result,
                    'effect_size': {
                        'cohen_d': float(effect_size),
                        'interpretation': StatisticalTests.interpret_effect_size(effect_size)
                    }
                }
        
        return results
    
    def generate_report(self, comparison_results: Dict) -> str:
        """生成统计比较报告
        
        Args:
            comparison_results: compare_all的返回结果
            
        Returns:
            Markdown格式的报告
        """
        report = []
        
        report.append("# Statistical Comparison Report\n")
        
        # 描述性统计
        report.append("## Descriptive Statistics\n")
        report.append("| Method | Mean | Median | Std | 95% CI |")
        report.append("|--------|------|--------|-----|--------|")
        
        for method, stats in comparison_results['descriptive_statistics'].items():
            ci_lower, ci_upper = stats['ci_95']
            report.append(
                f"| {method} | {stats['mean']:.4f} | {stats['median']:.4f} | "
                f"{stats['std']:.4f} | [{ci_lower:.4f}, {ci_upper:.4f}] |"
            )
        
        report.append("\n")
        
        # 总体检验
        if comparison_results['overall_test']:
            report.append("## Overall Test (Friedman)\n")
            overall = comparison_results['overall_test']
            report.append(f"- Statistic: {overall['statistic']:.4f}")
            report.append(f"- p-value: {overall['p_value']:.4f}")
            report.append(f"- Significant: {'Yes' if overall['is_significant'] else 'No'}\n")
        
        # 成对比较
        report.append("## Pairwise Comparisons\n")
        
        for comparison_name, results in comparison_results['pairwise_comparisons'].items():
            report.append(f"### {comparison_name}\n")
            
            # t检验
            t_test = results['t_test']
            report.append(f"**Paired t-test:**")
            report.append(f"- p-value: {t_test['p_value']:.4f}")
            report.append(f"- Significant: {'Yes' if t_test['is_significant'] else 'No'}")
            report.append(f"- Better method: {t_test['better_method']}\n")
            
            # 效应量
            effect = results['effect_size']
            report.append(f"**Effect Size:**")
            report.append(f"- Cohen's d: {effect['cohen_d']:.4f}")
            report.append(f"- Interpretation: {effect['interpretation']}\n")
        
        return "\n".join(report)
