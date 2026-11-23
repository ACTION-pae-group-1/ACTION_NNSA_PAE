# Model Training & Tuning Expert

This skill provides expertise in the implementation, training, and tuning of core models and algorithms.

## 🚀 Scope
- **Implementation**: Developing model architectures and training loops.
- **Bug Fixing**: Resolving critical math or logic errors in trainers and models.
- **Tuning**: Optimizing hyper-parameters for specific performance goals (e.g., precision, latency).
- **Tournament Management**: Coordinating the selection of the best architecture through empirical comparison.

## Core Methodologies
- **Algorithmic Approaches**: Implementation of specialized techniques (e.g., spectral subtraction, neural reconstruction, generative modeling).
- **Custom Layers/Losses**: Designing specialized components to meet project-specific quality standards.

## The Empirical Verification Cycle (TDD for Models)
Model "correctness" is verified through an empirical loop rather than simple boolean tests:
1. **Benchmark Setup**: Define a "Gold Standard" test set of paired samples.
2. **Hypothesis**: Propose a change with a measurable predicted outcome.
3. **Execution**: Implement the change.
4. **Quantitative Verification**: Use benchmark scripts to measure performance metrics.
5. **Qualitative Verification**: Perform human review to ensure no unwanted artifacts are introduced.

## Key Tuning Parameters
Identify and optimize the critical levers of the model:
- **Subtraction/Gain Factors**: Controlling the intensity of the operation.
- **Spectral Floors**: Preventing artifacts by maintaining a minimum signal level.
- **Resolution Parameters**: Balancing frequency vs. temporal resolution.
