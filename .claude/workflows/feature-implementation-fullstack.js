export const meta = {
  name: 'feature-implementation-fullstack',
  description: 'Implement a full-stack feature with TDD → (Design + Backend Ruff + Frontend Lint) → Final Verification',
  phases: [
    { title: 'TDD Implementation', detail: 'Write tests first, implement code, ensure GREEN' },
    { title: 'Parallel Review & Quality', detail: 'Design interrogation, backend ruff, frontend linting in parallel' },
    { title: 'Final Verification', detail: 'Merge results and verify full-stack readiness' },
  ],
}

const META = meta

function parseArgs(input) {
  if (!input) return { feature: '', config: {} }
  if (typeof input === 'string') return { feature: input, config: {} }
  return input
}

const tddPhase = async (featureDescription, config) => {
  const prompt = `Implement this full-stack feature following strict TDD (Red → Green) methodology:\n${featureDescription}\n\n**TDD Cycle:**\n1. Write failing tests first (both backend and frontend)\n2. Run tests and confirm RED (failure)\n3. Implement minimal code to make tests GREEN\n4. Run full test suite to verify no regressions\n5. Make small, safe refactors only\n\n**Critical rules:**\n- Always write tests before implementation\n- Make tests fail before making them pass\n- Keep implementation minimal (simplest code that passes tests)\n- Refactor only after tests are GREEN\n- Test both API contracts and UI behavior\n\n**Full-Stack Context:**\n- Backend test directory: ${config.backendTestDir}\n- Backend root: ${config.backendRoot}\n- Frontend root: ${config.frontendRoot}\n- App directory: ${config.backendAppDir}\n\nReturn a summary of:\n- Backend tests written and what they verify\n- Frontend tests written and UI scenarios covered\n- Implementation approach (API design, UI component structure)\n- Test results (all GREEN)\n- Any refactoring performed`.trim()
  return await agent(prompt, { label: 'tdd:fullstack-implementation', phase: META.phases[0].title, agentType: 'tdd-enforcer' })
}

const interrogationPhase = async (tddResults, config) => {
  const prompt = `Interrogate this full-stack TDD implementation rigorously.\n\n**Implementation Summary:**\n${tddResults?.summary || 'See the code changes'}\n\n**Interrogate across these dimensions:**\n\n1. **API Design**: Is the contract clear? Error cases handled? Version-safe?\n2. **Component Architecture**: Is the UI composable and testable? State management sound?\n3. **Assumptions**: System behavior, environment, user input expectations?\n4. **Edge Cases & Boundaries**: Empty, null, max values? Invalid inputs? Constraint violations?\n5. **Dependencies & Coupling**: API coupling, external services, circular dependencies?\n6. **Threat & Failure Modes**: What could break this in production? Recovery paths?\n7. **Alignment**: Does implementation match full-stack requirements?\n\nOutput a challenge report with:\n- API design flaws and improvements\n- Component/state-management risks\n- Assumptions and what breaks if wrong\n- Missing edge cases or error handling\n- Production risks and dependencies\n- Recommendations for strengthening\n\nRefactor until satisfied the design is sound.`.trim()
  try {
    return await agent(prompt, { label: 'interrogator:fullstack-design', phase: META.phases[1].title, agentType: 'interrogator' })
  } catch (e) {
    if (e.message && e.message.includes("agent type 'interrogator' not found")) {
      log(`Interrogator not available, falling back to code-reviewer for design review`)
      return await agent(prompt, { label: 'interrogator:fullstack-design', phase: META.phases[1].title, agentType: 'code-reviewer' })
    }
    throw e
  }
}

const backendRuffPhase = async (featureDescription, config) => {
  const prompt = `Run code quality checks on the backend implementation.\n\n**Feature Context:**\n${featureDescription}\n\n**Backend Ruff Quality Gates:**\n\n1. Run formatting: uv run ruff format .\n2. Run linting: uv run ruff check .\n3. Address findings: Remove unused imports, fix security issues (S-* rules never suppressed), address complexity, ensure PEP 8 compliance\n4. Verify: Run test suite to ensure no regressions\n\n**Configuration:**\n- Backend root: ${config.backendRoot}\n- App directory: ${config.backendAppDir}\n- Test directory: ${config.backendTestDir}\n\n**Report:**\n- What formatting was fixed\n- Code quality issues found and fixed\n- Any manual review items\n- Test suite results (must be GREEN)\n\nSecurity rules (S-*) must never be suppressed without documentation.`.trim()
  return await agent(prompt, { label: 'ruff:backend-quality', phase: META.phases[1].title, agentType: 'code-reviewer' })
}

const frontendLintPhase = async (featureDescription, config) => {
  const prompt = `Run code quality and linting checks on the frontend implementation.\n\n**Feature Context:**\n${featureDescription}\n\n**Frontend Quality Checks:**\n\n1. Run linting: npm run lint (or eslint depending on your setup)\n2. Run type checking: npm run type-check (TypeScript)\n3. Check for unused imports and dead code\n4. Verify component prop types are complete\n5. Check for accessibility issues (WCAG compliance)\n6. Run frontend tests: npm run test\n\n**Configuration:**\n- Frontend root: ${config.frontendRoot}\n- Looking for: src/ directory structure, test files, linting config\n\n**Report:**\n- Linting and type checking results\n- Code quality issues found and fixed\n- Accessibility issues identified and resolved\n- Frontend test results (must pass)\n- Any manual review items\n\nEnsure all tests pass and no warnings are suppressed without documentation.`.trim()
  return await agent(prompt, { label: 'lint:frontend-quality', phase: META.phases[1].title, agentType: 'code-reviewer' })
}

const verificationPhase = async (tddResults, interrogatorResults, backendRuffResults, frontendLintResults, config) => {
  const prompt = `Synthesize full-stack workflow results and verify implementation readiness.\n\n**Workflow Results Summary:**\n\nTDD: ${tddResults?.summary || 'Completed - all tests GREEN'}\n\nDesign Interrogation: ${interrogatorResults?.summary || 'Design challenges identified and addressed'}\n\nBackend Quality (Ruff): ${backendRuffResults?.summary || 'Quality gates passed'}\n\nFrontend Quality (Lint): ${frontendLintResults?.summary || 'Quality gates passed'}\n\n**Full-Stack Verification Checklist:**\n- All backend tests are GREEN (no regressions)\n- All frontend tests pass (no regressions)\n- Backend code follows project style (ruff passes)\n- Frontend code follows project style (linting passes)\n- No unhandled security warnings\n- API contract is clear and documented\n- UI components are accessible (WCAG)\n- Design challenges understood and mitigated\n- No unused code or imports\n- Ready for pre-commit hooks and PR review\n\n**Integration Points Verified:**\n- API endpoints properly tested and validated\n- Frontend correctly consumes API contract\n- Error handling flows from API through UI\n- State management is consistent\n- Type safety maintained across full-stack\n\n**Next Steps:**\n1. Review this summary for any remaining issues\n2. Commit with descriptive message\n3. Push to feature branch\n4. Pre-commit hooks will auto-verify\n5. Create PR for code review\n6. Optionally: Use documenter agent for API/UI documentation\n\n**Ready for merge review?** Verify all checklist items are complete.`.trim()
  return await agent(prompt, { label: 'verification:fullstack-check', phase: META.phases[2].title, agentType: 'code-reviewer' })
}

async function main() {
  const parsed = parseArgs(args)
  const featureDescription = parsed.feature || 'Full-stack feature implementation'
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
    const [interrogatorResults, backendRuffResults, frontendLintResults] = await parallel([
      () => interrogationPhase(tddResults, config),
      () => backendRuffPhase(featureDescription, config),
      () => frontendLintPhase(featureDescription, config),
    ])
    phase(META.phases[2].title)
    const verificationResults = await verificationPhase(tddResults, interrogatorResults, backendRuffResults, frontendLintResults, config)
    return { tdd: tddResults, interrogator: interrogatorResults, backendRuff: backendRuffResults, frontendLint: frontendLintResults, verification: verificationResults }
  } catch (error) {
    log(`Workflow error: ${error.message}`)
    throw error
  }
}

return await main()
