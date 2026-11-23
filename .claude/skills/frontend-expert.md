# Frontend Engineering Expert

This skill provides expertise in developing and maintaining a modern, type-safe frontend application.

## Core Tech Stack
- **Framework**: <e.g., React / Vue / Next.js>
- **Language**: TypeScript (Strict mode)
- **UI/Styling**: <e.g., CSS Modules / Tailwind / Styled Components>
- **Testing**:
    - **Component-Driven Development**: Using tools like Storybook for state and visual representation.
    - **E2E Testing**: Using tools like Playwright or Cypress for flow verification.
    - **Unit Testing**: Using tools like Vitest or Jest with property-based testing.

## The TDD Workflow (Non-Negotiable)
All new frontend features MUST follow this strict order:
1. **Visual State**: Define the component state and visual representation (e.g., a Storybook story).
2. **Interaction**: Assert behavior via interaction tests.
3. **E2E Test**: Write a test covering the user flow from the end-user perspective.
4. **Implementation**: Implement the component/logic to make the tests pass.

## Accessibility (A11y) Standards
The application must be accessible to all users, following industry standards:
- **WCAG Compliance**: Maintain strict contrast and focus management (e.g., Level AA).
- **Dynamic Updates**: Use appropriate ARIA roles for status updates and error messages.
- **Keyboard Navigation**: Every interactive element must be reachable via Tab and operable via Enter/Space.

## Responsive Guidelines
- **Mobile/Small Screens**: Components stack vertically for optimal readability.
- **Desktop/Large Screens**: Components utilize available screen real estate for efficient workflows (e.g., side-by-side layouts).
