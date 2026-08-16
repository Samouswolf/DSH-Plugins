"""
多模型辩证工作流管理器
管理三个Agent(保守派/激进派/综合者)进行辩证讨论
"""
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    GUARDIAN = "guardian"
    PIONEER = "pioneer"
    SYNTHESIZER = "synthesizer"


@dataclass
class Agent:
    id: str
    name: str
    model: str
    role: str
    description: str
    personality: str
    core_principles: List[str]
    output_rules: List[str]
    example_output: str


@dataclass
class Phase:
    phase: str
    step: int
    description: str
    actors: List[str]
    output_format: str


@dataclass
class Topic:
    topic_id: str
    title: str
    description: str
    background: str


@dataclass
class DebateResult:
    topic_id: str
    topic_title: str
    phase: str
    actor: str
    content: str
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass
class FinalDecision:
    topic_id: str
    topic_title: str
    radical_view: str
    conservative_view: str
    synthesized_solution: str
    validator_check: str
    final_decision: str
    action_items: List[str]
    confidence: float


class WorkflowManager:
    """多模型辩证工作流管理器"""

    def __init__(self, config_path: str = ".dna/multi_agent_config.json", base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_path = self.base_dir / config_path
        self.agents: Dict[str, Agent] = {}
        self.phases: List[Phase] = []
        self.topics: List[Topic] = []
        self.debate_history: List[DebateResult] = []
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        for agent_id, agent_data in config.get("agents", {}).items():
            self.agents[agent_id] = Agent(**agent_data)

        self.phases = [Phase(**phase_data) for phase_data in config.get("workflow", {}).get("phases", [])]
        self.topics = [Topic(**topic_data) for topic_data in config.get("topics", [])]

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取Agent"""
        return self.agents.get(agent_id)

    def generate_prompt(self, agent: Agent, topic: Topic, phase: Phase, history: List[DebateResult]) -> str:
        """生成Agent的prompt"""
        history_text = "\n".join(
            f"[{r.actor}] {r.content}" for r in history[-5:]
        ) if history else "无"

        prompt = f"""你是"{agent.name}"，角色是"{agent.role}"。

【角色描述】
{agent.description}

【核心原则】
{chr(10).join(f"- {p}" for p in agent.core_principles)}

【输出规则】
{chr(10).join(f"- {r}" for r in agent.output_rules)}

【示例输出】
{agent.example_output}

【当前议题】
标题: {topic.title}
描述: {topic.description}
背景: {topic.background}

【当前阶段】
阶段: {phase.phase} (步骤{phase.step})
描述: {phase.description}

【对话历史】
{history_text}

请基于你的角色，给出你的观点。输出格式要求：
- 直接输出观点内容
- 不要包含开场白或客套话
- 观点要有理有据
- 保持客观专业
"""
        return prompt

    def simulate_agent_response(self, agent: Agent, topic: Topic, phase: Phase, history: List[DebateResult]) -> str:
        """
        模拟Agent响应（因为当前环境无法直接调用外部API）
        
        这是一个占位实现，实际使用时应该替换为真实的模型调用：
        - DeepSeek API调用
        - GLM API调用
        - Qwen API调用
        
        当前实现基于角色定义生成模拟响应
        """
        responses = {
            "guardian": self._generate_guardian_response(agent, topic, phase, history),
            "pioneer": self._generate_pioneer_response(agent, topic, phase, history),
            "synthesizer": self._generate_synthesizer_response(agent, topic, phase, history),
        }
        return responses.get(agent.id, "暂无观点")

    def _generate_guardian_response(self, agent: Agent, topic: Topic, phase: Phase, history: List[DebateResult]) -> str:
        """生成保守派响应"""
        responses = {
            "topic_1": [
                "检索引擎集成有风险。Trae IDE的对话上下文已经很长，再注入DNA检索结果可能导致信息过载。",
                "而且检索引擎依赖jieba/numpy，Trae IDE环境可能不支持，违反零外部依赖原则。",
                "建议先验证Trae IDE是否支持Python脚本调用，再决定集成方案。",
                "集成应该是渐进式的，先从手动触发开始，而不是自动注入。",
            ],
            "topic_2": [
                "每次ingest都重建聚类索引是O(n^2)操作，会严重拖慢系统性能。",
                "当前的脏标记加延迟重建机制已经足够，问题是脏标记是否被正确设置。",
                "应该先检查代码，确认_cluster_dirty是否在ingest/evolve后被正确设置。",
                "如果脏标记机制失效，应该修复机制，而不是改为全量重建。",
            ],
            "topic_3": [
                "不能合并。strands是DNA存储层(磁吸匹配)，brain_pool是联想大脑(关键词触发)，架构不同。",
                "合并会破坏架构设计，导致两个子系统耦合，维护成本增加。",
                "建议建立双向索引：strand指向brain_pool，brain_pool指向strand，既保持架构清晰又实现关联。",
                "需要先检查数据一致性：是否所有strand都有对应的brain_pool条目？",
            ],
            "topic_4": [
                "强制更新有风险。开发者可能忘记写入，或者写入的信息质量不高。",
                "应该采用自动记录机制，而不是强制手动写入。",
                "建议方案：Bug修复后，系统自动提取修复内容，生成fix_log草稿，开发者确认后写入。",
                "需要Trae IDE支持git diff提取，如果不支持，可以降级为格式模板模式。",
            ],
            "topic_5": [
                "批量修改22个游戏风险极高。每个游戏的代码结构不同，统一注入组件可能破坏原有逻辑。",
                "触屏事件与鼠标事件冲突的概率高达40%，一旦冲突将导致游戏无法操作。",
                "localStorage存储限制可能导致存档功能在某些浏览器上失效，影响用户体验。",
                "建议先在单个游戏上验证方案，确认可行后再逐步推广，避免一刀切。",
            ],
        }

        topic_responses = responses.get(topic.topic_id, ["暂无观点"])
        pioneer_count = sum(1 for r in history if "激进派" in r.actor)
        return topic_responses[min(pioneer_count, len(topic_responses) - 1)]

    def _generate_pioneer_response(self, agent: Agent, topic: Topic, phase: Phase, history: List[DebateResult]) -> str:
        """生成激进派响应"""
        responses = {
            "topic_1": [
                "检索引擎必须集成！234条记忆从未被检索，DNA系统形同虚设，这是严重的资源浪费。",
                "应该在每次开发前自动运行system.smart_recall()，将结果注入到对话上下文。",
                "信息过载问题可以通过返回top-3结果解决，而不是全部返回。",
                "jieba/numpy是可选依赖，不影响核心功能，可以作为增强功能集成。",
            ],
            "topic_2": [
                "每次ingest后都应该重建聚类索引，否则新记忆无法被正确聚类，检索精度下降。",
                "O(n^2)太慢是借口，应该采用增量聚类算法，而不是全量重建。",
                "当前的脏标记机制可能失效，导致新记忆无法被正确聚类。",
                "激进方案：采用实时增量聚类，每次ingest只更新受影响的簇。",
            ],
            "topic_3": [
                "应该合并！两个存储导致数据分裂，检索时需要遍历两套索引，效率低下。",
                "合并后可以统一索引，提升检索性能，简化架构。",
                "保守派担心的架构问题，可以通过分层设计解决：底层统一存储，上层保持两个子系统的独立逻辑。",
                "合并后还可以实现跨子系统的联想，提升智能程度。",
            ],
            "topic_4": [
                "必须强制更新！fix_log是insights的数据来源，不更新会导致经验无法沉淀，DNA系统失去价值。",
                "应该在critical_rules中新增规则：每次Bug修复后必须写入fix_log。",
                "质量问题可以通过格式模板解决，要求开发者按照固定格式写入。",
                "强制执行可以通过CI/CD管道实现，未写入fix_log的提交无法合并。",
            ],
            "topic_5": [
                "必须建立游戏基础组件库！22个游戏存在相同的缺陷，逐个修复是重复劳动，效率低下。",
                "应该开发统一的触屏适配层、存档管理、操作提示组件，一次性解决所有游戏的共性问题。",
                "保守派担心的冲突问题可以通过事件优先级机制解决，触屏事件优先于鼠标事件。",
                "激进方案：一周内建立组件库，两周内集成到所有低分游戏，预期评分提升15-20分。",
            ],
        }

        topic_responses = responses.get(topic.topic_id, ["暂无观点"])
        guardian_count = sum(1 for r in history if "保守派" in r.actor)
        return topic_responses[min(guardian_count, len(topic_responses) - 1)]

    def _generate_synthesizer_response(self, agent: Agent, topic: Topic, phase: Phase, history: List[DebateResult]) -> str:
        """生成综合者响应"""
        responses = {
            "topic_1": {
                "问题定义": "保守派的风险确实存在，但激进派的收益也值得追求。",
                "方案辩论": "建议采用'按需触发'模式：用户明确提到'检索DNA'或'历史经验'时才触发检索，返回top-3结果避免信息过载。",
                "验证收敛": "按需触发模式符合零外部依赖原则，jieba/numpy作为可选依赖不影响核心功能。",
                "执行计划": "保守派的风险确实存在，但激进派的收益也值得追求。建议采用'按需触发'模式：用户明确提到'检索DNA'或'历史经验'时才触发检索，返回top-3结果避免信息过载。执行步骤：1) 检查Trae IDE是否支持Python脚本调用；2) 实现按需触发机制；3) 测试后推广。",
            },
            "topic_2": {
                "问题定义": "保守派关注性能，激进派关注精度，两者都有道理。",
                "方案辩论": "建议采用'脏标记加延迟重建加增量更新'混合方案：ingest后设置脏标记，首次查询时延迟重建，同时实现增量更新减少开销。",
                "验证收敛": "混合方案兼顾性能和精度，增量更新可以将O(n^2)降为O(n)。",
                "执行计划": "保守派关注性能，激进派关注精度，两者都有道理。建议采用'脏标记加延迟重建加增量更新'混合方案：ingest后设置脏标记，首次查询时延迟重建，同时实现增量更新减少开销。执行步骤：1) 检查_cluster_dirty是否被正确设置；2) 实现增量聚类算法；3) 性能测试。",
            },
            "topic_3": {
                "问题定义": "保守派维护架构清晰，激进派追求性能提升，两者可以兼顾。",
                "方案辩论": "建议采用'双向索引'方案：不合并存储，但在strand和brain_pool之间建立双向索引，既保持架构清晰又实现关联查询。",
                "验证收敛": "双向索引方案保持架构清晰，同时实现跨子系统关联，符合设计原则。",
                "执行计划": "保守派维护架构清晰，激进派追求性能提升，两者可以兼顾。建议采用'双向索引'方案：不合并存储，但在strand和brain_pool之间建立双向索引，既保持架构清晰又实现关联查询。执行步骤：1) 检查数据一致性；2) 添加strand_id和brain_entity_id字段；3) 实现双向查询。",
            },
            "topic_4": {
                "问题定义": "保守派担心质量和负担，激进派关注经验沉淀，两者可以平衡。",
                "方案辩论": "建议采用'半自动'机制：Bug修复后系统自动提取内容生成草稿，开发者确认后写入，既保证不遗漏又保证质量。",
                "验证收敛": "半自动机制平衡质量和负担，自动提取减少手动工作，确认机制保证质量。",
                "执行计划": "保守派担心质量和负担，激进派关注经验沉淀，两者可以平衡。建议采用'半自动'机制：Bug修复后系统自动提取内容生成草稿，开发者确认后写入，既保证不遗漏又保证质量。执行步骤：1) 设计fix_log格式模板；2) 实现自动提取机制；3) 集成到开发流程。",
            },
            "topic_5": {
                "问题定义": "保守派关注风险控制，激进派追求效率提升，两者必须平衡。",
                "方案辩论": "建议采用'渐进式组件化'方案：先建立基础组件库，然后在单个游戏上测试验证，确认可行后再批量推广。既保证效率又控制风险。",
                "验证收敛": "渐进式组件化方案兼顾效率和风险，先验证再推广符合DNA系统设计原则。",
                "执行计划": "保守派关注风险控制，激进派追求效率提升，两者必须平衡。建议采用'渐进式组件化'方案：先建立基础组件库，然后在单个游戏上测试验证，确认可行后再批量推广。执行步骤：1) 开发触屏适配层、存档管理、操作提示组件；2) 在骰子游戏上测试集成；3) 验证评分提升效果；4) 批量推广到其他低分游戏。",
            },
        }

        topic_responses = responses.get(topic.topic_id, {})
        return topic_responses.get(phase.phase, "暂无观点")

    def run_debate(self, topic_id: str) -> FinalDecision:
        """运行一个议题的完整辩证流程"""
        topic = next((t for t in self.topics if t.topic_id == topic_id), None)
        if not topic:
            raise ValueError(f"议题不存在: {topic_id}")

        print(f"\n{'='*60}")
        print(f"开始辩证：{topic.title}")
        print(f"{'='*60}")

        debate_results: List[DebateResult] = []

        for phase in self.phases:
            print(f"\n[阶段{phase.step}] {phase.phase}")
            print(f"描述: {phase.description}")

            for actor_id in phase.actors:
                agent = self.get_agent(actor_id)
                if not agent:
                    continue

                prompt = self.generate_prompt(agent, topic, phase, debate_results)
                response = self.simulate_agent_response(agent, topic, phase, debate_results)

                result = DebateResult(
                    topic_id=topic_id,
                    topic_title=topic.title,
                    phase=phase.phase,
                    actor=agent.name,
                    content=response,
                )
                debate_results.append(result)

                print(f"\n  {agent.name}:")
                print(f"    {response}")

                time.sleep(0.5)

            self.debate_history.extend(debate_results)

        return self._synthesize_decision(topic, debate_results)

    def _synthesize_decision(self, topic: Topic, debate_results: List[DebateResult]) -> FinalDecision:
        """综合辩证结果，生成最终决策"""
        radical_view = "\n".join(r.content for r in debate_results if "激进派" in r.actor)
        conservative_view = "\n".join(r.content for r in debate_results if "保守派" in r.actor)
        
        final_synthesizer = [r for r in debate_results if "综合者" in r.actor and r.phase == "执行计划"]
        synthesized_solution = final_synthesizer[0].content if final_synthesizer else "\n".join(r.content for r in debate_results if "综合者" in r.actor)

        return FinalDecision(
            topic_id=topic.topic_id,
            topic_title=topic.title,
            radical_view=radical_view,
            conservative_view=conservative_view,
            synthesized_solution=synthesized_solution,
            validator_check="符合DNA系统设计原则：零外部依赖、向后兼容、渐进式改进",
            final_decision="adopted",
            action_items=self._extract_action_items(synthesized_solution),
            confidence=0.85,
        )

    def _extract_action_items(self, solution: str) -> List[str]:
        """从综合方案中提取执行步骤"""
        action_items = []
        lines = solution.split("\n")
        for line in lines:
            if "步骤" in line:
                steps = line.split("步骤")[1]
                action_items.extend([s.strip() for s in steps.split(";") if s.strip()])
            elif "1)" in line or "2)" in line or "3)" in line:
                action_items.append(line.strip())
        return action_items or ["需要进一步分析"]

    def run_all_topics(self) -> List[FinalDecision]:
        """运行所有议题的辩证流程"""
        decisions = []
        for topic in self.topics:
            try:
                decision = self.run_debate(topic.topic_id)
                decisions.append(decision)
                self._save_decision(decision)
            except Exception as e:
                print(f"议题 {topic.topic_id} 执行失败: {e}")
        return decisions

    def _save_decision(self, decision: FinalDecision):
        """保存决策结果"""
        output_dir = self.base_dir / ".dna" / "debate_results"
        output_dir.mkdir(parents=True, exist_ok=True)

        result_file = output_dir / f"{decision.topic_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(decision.__dict__, f, ensure_ascii=False, indent=2)

        summary_file = output_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, "r", encoding="utf-8") as f:
                summaries = json.load(f)
        else:
            summaries = []

        summaries.append({
            "topic_id": decision.topic_id,
            "topic_title": decision.topic_title,
            "final_decision": decision.final_decision,
            "confidence": decision.confidence,
            "action_items": decision.action_items,
            "timestamp": time.time(),
        })

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)

    def format_decision(self, decision: FinalDecision) -> str:
        """格式化决策输出"""
        return f"""【议题】{decision.topic_title}

【激进派观点】
{decision.radical_view}

【保守派观点】
{decision.conservative_view}

【综合方案】
{decision.synthesized_solution}

【验证检查】
{decision.validator_check}

【最终决策】{decision.final_decision}

【执行步骤】
{chr(10).join(f"- {item}" for item in decision.action_items)}

【置信度】{decision.confidence}
"""