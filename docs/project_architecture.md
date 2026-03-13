# 项目架构说明

本项目已按照 `dirroot.md` 的约定完成标准化骨架初始化。

## 顶层目录

- `src/`：核心源代码
- `tests/`：单元、集成与端到端测试
- `docs/`：规范、架构与重构说明
- `data/`：原始、处理后和示例数据
- `scripts/`：自动化脚本
- `configs/`：配置文件
- `logs/`：运行日志
- `notebooks/`：实验与分析笔记
- `results/`：输出结果
- `docker/`：容器化相关内容
- `experiments/`：实验配置、运行结果与指标
- `.aiconfig/`：本次结构初始化记录

## `src/` 分层

- `core/`：核心逻辑
- `modules/`：功能模块
- `utils/`：工具函数
- `interfaces/`：接口层
- `config/`：默认配置
- `data/`：数据访问层
- `pipelines/`：流程编排
