# Generative Model Expert

**Activated when standard suppressive models fail to meet the quality bar.**

## Specialty
Targeted reconstruction via generative models—not simply removing unwanted components, but reconstructing the "clean" signal conditioned on target embeddings.

## Key Architectures
- **Flow-based Models**: Using rectified flow matching for fast, high-quality reconstruction.
- **Diffusion Transformers (DiT)**: Utilizing latent diffusion and cross-attention for SOTA quality.
- **Zero-Shot Inversion**: Using latent space optimization for immediate results without training.

## Conditioning Strategy
- **Embedding-based Conditioning**: Extracting embeddings from a target sample and using them as cross-attention conditioning in the generative model.

## Integration into Tournament
1. **Spike**: Run zero-shot experiments to evaluate potential.
2. **Iterative Training**: Provision high-performance compute for iterative training of generative models.
3. **Comparison**: Feed results into the same evaluation harness as standard models.
4. **Validation**: Mandatory human review before promotion.

## Implementation Requirements
- **Dedicated Training**: Separate scripts from the main pipeline to handle generative complexity.
- **Metadata Versioning**: Checkpoints must include detailed metadata about the training run.
- **Observability**: Adherence to the project's structured logging and metrics standards.
