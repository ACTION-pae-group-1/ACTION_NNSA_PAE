export const meta = {
  name: 'feature-implementation-parallel',
  description: 'Implement a feature with TDD → (Interrogator + Ruff in parallel) → Final Verification',
  phases: [
    { title: 'TDD Implementation', detail: 'Write tests first, implement code, ensure GREEN' },
    { title: 'Parallel Review & Quality', detail: 'Run design interrogation and ruff checks in parallel' },
    { title: 'Final Verification', detail: 'Merge results and verify readiness' },
  ],
}

const META = meta

function parseArgs(input) {
  if (!input) return { feature: '', config: {} }
  if (typeof input === 'string') return { feature: input, config: {} }
  return input
}

const tddPhase = async (featureDescription, config) => {
  const prompt = `Implement this feature following strict TDD (Red → Green) methodology:\n${featureDescription}\n\n**TDD Cycle:**\n1. Write failing test(s) first that define the feature contract\n2. Run tests and confirm RED (failure)\n3. Implement minimal code to make tests GREEN\n4. Run full test suite to verify no regressions\n5. Make small, safe refactors only\n\n**Critical rules:**\n- Always write test first, then implementation\n- Make tests fail before making them pass\n- Keep implementation minimal (simplest code that passes tests)\n- Refactor only after tests are GREEN\n\n**Context:**\n- Test directory: ${config.backendTestDir}\n- Backend root: ${config.backendRoot}\n- App directory: ${config.backendAppDir}\n\nReturn a summary of:\n- Tests written and what they verify\n- Implementation approach and key decisions\n- Test results (GREEN)\n- Any refactoring performed`.trim()
  return await agent(prompt, { label: 'tdd:implementation', phase: META.phases[0].title, agentType: 'tdd-enforcer' })
}

const interrogationPhase = async (tddResults, config) => {
  const prompt = `Interrogate this TDD implementation rigorously.\n\n**Implementation Summary:**\n${tddResults?.summary || 'See the code changes'}\n\n**Interrogate across these dimensions:**\n\n1. **Assumptions**: What are we assuming about system behavior, environment, user input?\n2. **Edge Cases & Boundaries**: What happens at extremes?\n3. **Dependencies & Coupling**: What interconnections exist?\n4. **Threat & Failure Modes**: What could break this?\n5. **Alignment**: Does this match requirements?\n\nOutput a challenge report with:\n- Assumptions and what breaks if wrong\n- Gaps and missing scenarios\n- Risks and dependencies\n- Ambiguities and unclear decisions\n- Recommendations for strengthening\n\nRefactor until satisfied the design is sound.`.trim()
  try {
    return await agent(prompt, { label: 'interrogator:design-challenge', phase: META.phases[1].title, agentType: 'interrogator' })
  } catch (e) {
    if (e.message && e.message.includes("agent type 'interrogator' not found")) {
      log(`Interrogator not available, falling back to code-reviewer for design review`)
      return await agent(prompt, { label: 'interrogator:design-challenge', phase: META.phases[1].title, agentType: 'code-reviewer' })
    }
    throw e
  }
}

const ruffPhase = async (featureDescription, config) => {
  const prompt = `Run code quality checks on the implementation.\n\n**Feature Context:**\n${featureDescription}\n\n**Ruff Quality Gates:**\n\n1. Run formatting: uv run ruff format .\n2. Run linting: uv run ruff check .\n3. Address findings: Remove unused imports, fix security issues (S-* rules never suppressed), address complexity, ensure PEP 8 compliance\n4. Verify: Run test suite to ensure no regressions\n\n**Configuration:**\n- Backend root: ${config.backendRoot}\n- App directory: ${config.backendAppDir}\n\n**Report:**\n- What formatting was fixed\n- Code quality issues found and fixed\n- Any manual review items\n- Test suite results (must be GREEN)\n\nSecurity rules (S-*) must never be suppressed without documentation.`.trim()
  return await agent(prompt, { label: 'ruff:code-quality', phase: META.phases[1].title, agentType: 'code-reviewer' })
}

const verificationPhase = async (tddResults, interrogatorResults, ruffResults, config) => {
  const prompt = `Synthesize the results and verify implementation readiness.\n\n**Workflow Results Summary:**\n\nTDD: ${tddResults?.summary || 'Completed - all tests GREEN'}\n\nDesign Interrogation: ${interrogatorResults?.summary || 'Design challenges identified and addressed'}\n\nCode Quality (Ruff): ${ruffResults?.summary || 'Quality gates passed'}\n\n**Final Checklist:**\n- All tests are GREEN (no regressions)\n- Code follows project style (ruff passes)\n- No unhandled security warnings\n- Design challenges understood and mitigated\n- No unused code or imports\n- Ready for pre-commit hooks\n\n**Next Steps:**\n1. Review this summary for any remaining issues\n2. Commit with descriptive message\n3. Push to feature branch\n4. Pre-commit hooks will auto-verify\n5. Create PR for code review\n6. Optionally: Use documenter agent for API/user documentation\n\n**Ready for merge review?** Verify all checklist items are complete.`.trim()
  return await agent(prompt, { label: 'verification:final-check', phase: META.phases[2].title, agentType: 'code-reviewer' })
}

async function main() {
  const parsed = parseArgs(args)
  const featureDescription = parsed.feature || 'Feature implementation'
  const inputConfig = parsed.config || {}
  const config = {
    backendTestDir: inputConfig.backendTestDir || 'app/tests',
    backendAppDir: inputConfig.backendAppDir || 'app',
    backendRoot: inputConfig.backendRoot || 'backend',
    frontendRoot: inputConfig.frontendRoot || 'frontend',
  }
  try {
    phase(META.phases[0].title)
    const tddResults = await tddPhase(featureDescription, config)
    phase(META.phases[1].title)
    const [interrogatorResults, ruffResults] = await parallel([
      () => interrogationPhase(tddResults, config),
      () => ruffPhase(featureDescription, config),
    ])
    phase(META.phases[2].title)
    const verificationResults = await verificationPhase(tddResults, interrogatorResults, ruffResults, config)
    return { tdd: tddResults, interrogator: interrogatorResults, ruff: ruffResults, verification: verificationResults }
  } catch (error) {
    log(`Workflow error: ${error.message}`)
    throw error
  }
}

return await main()
