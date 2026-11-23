export const meta = {
  name: 'mcp-development-parallel',
  description: 'Build an MCP server with TDD → (Design Challenge + Quality) → (Build + Eval) → Verify',
  phases: [
    { title: 'TDD Implementation', detail: 'Write failing tests, implement tools, ensure GREEN' },
    { title: 'Parallel Review', detail: 'Design interrogation and code quality checks in parallel' },
    { title: 'Parallel Build & Eval', detail: 'Build server and run LLM-as-judge evaluation in parallel' },
    { title: 'Final Verification', detail: 'Verify server readiness and deployment checklist' },
  ],
}

function parseArgs(input) {
  if (!input) return { feature: '', config: {} }
  if (typeof input === 'string') return { feature: input, config: {} }
  return input
}

const tddPhase = async (serverDescription, config) => {
  const prompt = `Build an MCP server following strict TDD (Red → Green) methodology:\n${serverDescription}\n\n**TDD Cycle for MCP:**\n1. Write failing tests first that define tool contracts\n2. Run tests and confirm RED (failure)\n3. Implement minimal tools and handlers to make tests GREEN\n4. Run full test suite to verify no regressions\n5. Make small, safe refactors only\n\n**Critical rules:**\n- Always write tests before implementation\n- Make tests fail before making them pass\n- Define tool schemas and responses clearly in tests\n- Refactor only after tests are GREEN\n- Test error handling and edge cases\n\n**MCP Server Context:**\n- Framework: ${config.framework || 'FastMCP'} (Python) or MCP SDK (Node.js)\n- Tools directory: ${config.toolsDir || 'src/tools'}\n- Tests directory: ${config.testsDir || 'tests'}\n- Server root: ${config.serverRoot || '.'}\n\nReturn a summary of:\n- Tool tests written and what they verify\n- Tool implementations (handlers, schemas)\n- Error handling and validation\n- Test results (all GREEN)\n- Any refactoring performed`.trim()
  return await agent(prompt, { label: 'tdd:mcp-tools', phase: 'TDD Implementation', agentType: 'tdd-enforcer' })
}

const designChallengePhase = async (tddResults, config) => {
  const prompt = `Interrogate this MCP server design rigorously.\n\n**Server Summary:**\n${tddResults?.summary || 'See the tool implementations'}\n\n**Interrogate across these dimensions:**\n\n1. **Tool Contracts**: Are schemas clear and complete? Error responses defined?\n2. **Resource Management**: Rate limiting implemented? Timeout handling? Resource cleanup?\n3. **Error Handling**: All error paths tested? User-friendly error messages?\n4. **Security**: Input validation on all tools? No command injection? Safe resource access?\n5. **Assumptions**: What's assumed about client behavior, network, resources?\n6. **Edge Cases**: Empty, null, invalid inputs? Concurrent access? Large payloads?\n7. **Production Readiness**: Logging, monitoring hooks? Graceful degradation?\n\nOutput a challenge report with:\n- Tool contract gaps and improvements\n- Error handling and validation issues\n- Security concerns and mitigations\n- Production readiness gaps\n- Resource management risks\n- Recommendations for strengthening\n\nRefactor until satisfied the server design is sound.`.trim()
  try {
    return await agent(prompt, { label: 'interrogator:mcp-design', phase: 'Parallel Review', agentType: 'interrogator' })
  } catch (e) {
    if (e.message && e.message.includes("agent type 'interrogator' not found")) {
      log(`Interrogator not available, falling back to code-reviewer for design review`)
      return await agent(prompt, { label: 'interrogator:mcp-design', phase: 'Parallel Review', agentType: 'code-reviewer' })
    }
    throw e
  }
}

const qualityCheckPhase = async (serverDescription, config) => {
  const prompt = `Run code quality checks on the MCP server implementation.\n\n**Server Context:**\n${serverDescription}\n\n**Code Quality Gates:**\n\n1. Code formatting and style:\n   - Python: uv run ruff format . && uv run ruff check .\n   - Node: npm run lint && npm run format\n2. Type checking:\n   - Python: mypy src/ (if configured)\n   - Node: npm run type-check\n3. Security scanning:\n   - Python: uv run ruff check . (security rules: S-*)\n   - Node: npm audit\n4. Complexity and maintainability:\n   - Remove unused code and imports\n   - Address code smells\n   - Ensure clear docstrings\n5. Run full test suite\n\n**Configuration:**\n- Framework: ${config.framework || 'FastMCP'}\n- Server root: ${config.serverRoot || '.'}\n- Tests directory: ${config.testsDir || 'tests'}\n\n**Report:**\n- Code style fixes applied\n- Security issues found and fixed\n- Type checking results\n- Test suite results (must be GREEN)\n- Any items requiring manual review\n\nSecurity rules must never be suppressed without documentation.`.trim()
  return await agent(prompt, { label: 'quality:mcp-checks', phase: 'Parallel Review', agentType: 'code-reviewer' })
}

const buildPhase = async (serverDescription, config) => {
  const prompt = `Build and package the MCP server for deployment.\n\n**Server Context:**\n${serverDescription}\n\n**Build Steps:**\n\n1. Install dependencies:\n   - Python: uv sync\n   - Node: npm install\n2. Run complete test suite:\n   - Python: uv run pytest\n   - Node: npm test\n3. Build/bundle:\n   - Python: uv build (if building package)\n   - Node: npm run build (if applicable)\n4. Verify server can start:\n   - Test the main entry point\n   - Verify tools are discoverable\n5. Create server metadata:\n   - Server name, version\n   - Supported tools list\n   - Requirements/dependencies\n\n**Configuration:**\n- Framework: ${config.framework || 'FastMCP'}\n- Server root: ${config.serverRoot || '.'}\n- Entry point: ${config.entryPoint || 'src/server.py or src/index.js'}\n\n**Report:**\n- Build output and any warnings\n- Test results summary\n- Dependency list\n- Server metadata\n- Deployment package contents`.trim()
  return await agent(prompt, { label: 'build:mcp-server', phase: 'Parallel Build & Eval', agentType: 'mcp-builder' })
}

const evaluationPhase = async (serverDescription, config) => {
  const prompt = `Build and run LLM-as-judge evaluation for this MCP server.\n\n**Server Context:**\n${serverDescription}\n\n**Evaluation Framework:**\n\n1. Create evaluation harness (Phoenix-based):\n   - Define evaluation dataset with realistic tasks\n   - Create judges that score tool usage (correctness, efficiency, error handling)\n   - Set performance thresholds\n\n2. Define evaluation scenarios:\n   - Happy path: Basic usage of each tool\n   - Error paths: Invalid inputs, edge cases\n   - Complex scenarios: Multi-step operations, state management\n\n3. Run evaluation:\n   - Execute LLM agent using server tools\n   - Judge outputs based on correctness, efficiency, UX\n   - Score each scenario\n\n4. Analyze results:\n   - Identify tool improvements\n   - Score overall server readiness\n   - Flag any missing capabilities\n\n**Configuration:**\n- Framework: ${config.framework || 'FastMCP'}\n- Server root: ${config.serverRoot || '.'}\n- Eval directory: ${config.evalDir || 'eval'}\n\n**Report:**\n- Evaluation scenarios and results\n- Tool usage patterns observed\n- Correctness/efficiency scores\n- Error handling assessment\n- Recommendations for improvement`.trim()
  return await agent(prompt, { label: 'eval:mcp-server', phase: 'Parallel Build & Eval', agentType: 'mcp-eval' })
}

const verificationPhase = async (tddResults, designResults, qualityResults, buildResults, evalResults) => {
  const prompt = `Synthesize MCP server workflow results and verify deployment readiness.\n\n**Workflow Results Summary:**\n\nTDD: ${tddResults?.summary || 'All tests GREEN'}\nDesign Challenge: ${designResults?.summary || 'Design validated'}\nCode Quality: ${qualityResults?.summary || 'Quality gates passed'}\nBuild: ${buildResults?.summary || 'Build successful'}\nEvaluation: ${evalResults?.summary || 'Evaluation complete'}\n\n**MCP Server Verification Checklist:**\n- All unit tests pass (GREEN)\n- All integration tests pass\n- All tools have complete schemas\n- Error handling comprehensive\n- Code follows project style\n- No security warnings\n- Design validated against production scenarios\n- Build succeeds without warnings\n- LLM-as-judge evaluation passed\n- Server starts cleanly\n- All tools discoverable\n\n**Deployment Readiness:**\n- [ ] Server metadata complete (name, version, description)\n- [ ] Dependency list accurate\n- [ ] Error messages user-friendly\n- [ ] Rate limiting configured (if applicable)\n- [ ] Logging configured appropriately\n- [ ] Documentation complete\n- [ ] Example usage provided\n\n**Next Steps:**\n1. Review this checklist\n2. Address any remaining issues\n3. Commit with descriptive message\n4. Push to feature branch\n5. Create PR for deployment\n6. Deploy to production registry\n\n**Ready for production?** Verify all checklist items are complete.`.trim()
  return await agent(prompt, { label: 'verification:mcp-ready', phase: 'Final Verification', agentType: 'code-reviewer' })
}

const PHASES = {
  TDD: 'TDD Implementation',
  REVIEW: 'Parallel Review',
  BUILD: 'Parallel Build & Eval',
  VERIFY: 'Final Verification',
}

const parsed = parseArgs(typeof args !== 'undefined' ? args : null)
const serverDescription = parsed.feature || 'PARS MCP server with WBS hierarchy tools'
const inputConfig = parsed.config || {}
const config = {
  framework: inputConfig.framework || 'FastMCP',
  serverRoot: inputConfig.serverRoot || '.',
  toolsDir: inputConfig.toolsDir || 'src/tools',
  testsDir: inputConfig.testsDir || 'tests',
  evalDir: inputConfig.evalDir || 'eval',
  entryPoint: inputConfig.entryPoint || 'src/server.py',
}

phase(PHASES.TDD)
const tddResults = await tddPhase(serverDescription, config)

phase(PHASES.REVIEW)
const [designResults, qualityResults] = await parallel([
  () => designChallengePhase(tddResults, config),
  () => qualityCheckPhase(serverDescription, config),
])

phase(PHASES.BUILD)
const [buildResults, evalResults] = await parallel([
  () => buildPhase(serverDescription, config),
  () => evaluationPhase(serverDescription, config),
])

phase(PHASES.VERIFY)
const verificationResults = await verificationPhase(tddResults, designResults, qualityResults, buildResults, evalResults)

({
  tdd: tddResults,
  design: designResults,
  quality: qualityResults,
  build: buildResults,
  eval: evalResults,
  verification: verificationResults,
})
