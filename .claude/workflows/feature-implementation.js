export const meta = {
  name: 'feature-implementation',
  description: 'Implement a feature following TDD → Interrogator → Ruff → Verification workflow',
  phases: [
    { title: 'TDD Implementation', detail: 'Write tests first, implement code, ensure GREEN' },
    { title: 'Design Interrogation', detail: 'Challenge assumptions, probe edge cases, validate design' },
    { title: 'Code Quality', detail: 'Run ruff checks, fix formatting, enforce standards' },
    { title: 'Final Verification', detail: 'Verify tests, ruff checks, security, and merge readiness' },
  ],
}

const META = meta

function parseArgs(input) {
  if (!input) return { feature: '', config: {} }
  if (typeof input === 'string') return { feature: input, config: {} }
  return input
}

const tddPhase = async (featureDescription, config) => {
  const prompt = `Implement this feature following strict TDD (Red → Green) methodology:\n${featureDescription}\n\n**TDD Cycle:**\n1. Write failing test(s) first that define the feature contract\n2. Run tests and confirm RED (failure)\n3. Implement minimal code to make tests GREEN\n4. Run full test suite to verify no regressions\n5. Make small, safe refactors only\n\n**Critical rules:**\n- Always write test first, then implementation\n- Make tests fail before making them pass\n- Keep implementation minimal (simplest code that passes tests)\n- Refactor only after tests are GREEN\n\n**Project Configuration:**\n- Backend root: ${config.backendRoot}\n- Test directory: ${config.backendTestDir}\n- App directory: ${config.backendAppDir}\n\nReturn a summary of:\n- Tests written and what they verify\n- Implementation approach and key decisions\n- Test results (GREEN)\n- Any refactoring performed`.trim()
  return await agent(prompt, { label: 'tdd:implementation', phase: META.phases[0].title, agentType: 'tdd-enforcer' })
}

const interrogationPhase = async (tddResults, config) => {
  const prompt = `Interrogate this TDD implementation rigorously.\n\n**Implementation Summary:**\n${tddResults?.summary || 'See the code changes'}\n\n**Interrogate across these dimensions:**\n1. **Assumptions**: What are we assuming about system behavior, environment, user input?\n2. **Edge Cases & Boundaries**: What happens at extremes?\n3. **Dependencies & Coupling**: What interconnections exist?\n4. **Threat & Failure Modes**: What could break this?\n5. **Alignment**: Does this match requirements?\n\nOutput a challenge report with:\n- Assumptions and what breaks if wrong\n- Gaps and missing scenarios\n- Risks and dependencies\n- Ambiguities and unclear decisions\n- Recommendations for strengthening\n\nRefactor until satisfied the design is sound.`.trim()
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
  const prompt = `Run code quality checks and cleanup on the implementation for this feature:\n${featureDescription}\n\n**Ruff Quality Gates:**\n1. Run formatting: uv run ruff format .\n2. Run linting: uv run ruff check .\n3. Address findings: Remove unused imports, fix security issues (S-* rules never suppressed), address complexity, ensure PEP 8 compliance\n4. Verify: Run test suite again to ensure no regressions\n\n**Project Configuration:**\n- Backend root: ${config.backendRoot}\n- Test directory: ${config.backendTestDir}\n\n**Report:**\n- What formatting was fixed\n- Code quality issues found and fixed\n- Any manual review items\n- Test suite results (must be GREEN)\n\nSecurity rules (S-*) must never be suppressed without documentation.`.trim()
  return await agent(prompt, { label: 'ruff:code-quality', phase: META.phases[2].title, agentType: 'code-reviewer' })
}

const verificationPhase = async (tddResults, interrogatorResults, ruffResults, config) => {
  const prompt = `Summarize the feature implementation workflow and verify readiness.\n\n**Workflow Summary:**\nTDD: ${tddResults?.summary || 'Completed'}\nDesign Interrogation: ${interrogatorResults?.summary || 'Addressed'}\nCode Quality: ${ruffResults?.summary || 'Passed'}\n\n**Verification Checklist:**\n- All tests are GREEN\n- Code follows project style\n- No security warnings\n- Design challenges mitigated\n- No unused code or imports\n- Changes are committed\n\n**Next Steps:**\n1. Review checklist\n2. Commit changes\n3. Push to feature branch\n4. Create PR for review\n\n**Ready for merge review?** Yes, if all checkboxes are complete.`.trim()
  return await agent(prompt, { label: 'verification:final-check', phase: META.phases[3].title, agentType: 'code-reviewer' })
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
  const results = { tdd: null, interrogator: null, ruff: null, verification: null }
  try {
    phase(META.phases[0].title)
    results.tdd = await tddPhase(featureDescription, config)
    phase(META.phases[1].title)
    results.interrogator = await interrogationPhase(results.tdd, config)
    phase(META.phases[2].title)
    results.ruff = await ruffPhase(featureDescription, config)
    phase(META.phases[3].title)
    results.verification = await verificationPhase(results.tdd, results.interrogator, results.ruff, config)
    return results
  } catch (error) {
    log(`Workflow error: ${error.message}`)
    throw error
  }
}

return await main()
