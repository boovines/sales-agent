---
name: prd
description: "Generate a Product Requirements Document (PRD) for a new feature. Use when planning a feature, starting a new project, or when asked to create a PRD. Triggers on: create a prd, write prd for, plan this feature, requirements for, spec out."
---

# PRD Generator

Create detailed Product Requirements Documents that are clear, actionable, and suitable for implementation.

---

## The Job

1. Receive a feature description from the user
2. Ask 5-8 essential clarifying questions (with lettered options)
3. Generate a structured PRD based on answers
4. Save to `tasks/prd-[feature-name].md`

**Important:** Do NOT start implementing. Just create the PRD.

---

## Step 1: Clarifying Questions

Ask only critical questions where the initial prompt is ambiguous. Focus on:

- **Problem/Goal:** What problem does this solve?
- **Core Functionality:** What are the key actions?
- **Scope/Boundaries:** What should it NOT do?
- **Success Criteria:** How do we know it's done?
- **UI/UX Requirements:** What's the design aesthetic and user flow?
- **Tech Stack Specifics:** Any specific libraries or patterns?
- **Security Requirements:** What sensitive data is involved?
- **AI/Agent Requirements:** Does this need LLM orchestration or automation?

### Format Questions Like This:

```
1. What is the primary goal of this feature?
   A. Improve user onboarding experience
   B. Increase user retention
   C. Reduce support burden
   D. Other: [please specify]

2. Who is the target user?
   A. New users only
   B. Existing users only
   C. All users
   D. Admin users only

3. What is the scope?
   A. Minimal viable version
   B. Full-featured implementation
   C. Just the backend/API
   D. Just the UI

4. What's the UI design aesthetic?
   A. Minimal and clean
   B. Bold and colorful
   C. Modern with animations
   D. Match existing app style

5. What sensitive data is involved?
   A. User passwords/authentication
   B. Payment information
   C. Personal user data
   D. None

6. Does this feature need AI/LLM capabilities?
   A. Yes - classification or categorization
   B. Yes - structured reasoning or decision-making
   C. Yes - workflow automation
   D. No AI needed
```

This lets users respond with "1A, 2C, 3B, 4C, 5A, 6B" for quick iteration.

---

## Step 2: PRD Structure

Generate the PRD with these **mandatory sections** in this exact order:

### 1. Product Overview

**REQUIRED: Single paragraph containing:**
- What the product/feature is
- Who it's for (target users)
- Tech stack being used

**Tech Stack:**
- **Frontend:** Next.js + React (TypeScript) for embedded UI components, deployed on Vercel
- **Backend:** Node.js (TypeScript) for core backend services
- **Agent Services:** Python services for agent orchestration and background workers
- **Database:** Convex for structured data, real-time sync, deployment memory with built-in vector search
- **Infrastructure:** AWS (ECS/Lambda) for Python services, Vercel for frontend
- **AI:** OpenAI models (GPT-4.1-class) for issue classification, structured reasoning, and workflow automation with semantic retrieval
- **Dev Tools:** GitHub, Docker, CI/CD, Cursor, Claude Code, Warp AI

**Example:**
```markdown
## Product Overview

[Feature Name] is a [type of application/feature] designed for [target users] to [primary benefit/problem solved]. Built with Next.js and React (TypeScript) for the frontend deployed on Vercel, Node.js (TypeScript) for core backend services, and Python for agent orchestration and background workers running on AWS ECS/Lambda. Data is managed in Convex providing real-time sync and vector search capabilities, with OpenAI GPT-4.1 models powering intelligent classification, reasoning, and workflow automation.
```

### 2. File Structure

**REQUIRED: Specify where files will be organized.**

Include:
- Directory structure for frontend (Next.js/React)
- Backend services (Node.js)
- Python agent services
- Shared types and utilities
- Infrastructure configuration

**Example:**
```markdown
## File Structure

```
project-root/
├── frontend/                    # Next.js + React (TypeScript)
│   ├── app/                    # Next.js 13+ app directory
│   │   ├── (routes)/           # Route groups
│   │   ├── api/                # API routes
│   │   └── layout.tsx          # Root layout
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   ├── features/           # Feature-specific components
│   │   └── layouts/            # Layout components
│   ├── lib/
│   │   ├── convex/             # Convex client and queries
│   │   ├── openai/             # OpenAI client utilities
│   │   └── utils/              # Utility functions
│   ├── hooks/                  # Custom React hooks
│   ├── types/                  # TypeScript type definitions
│   └── public/                 # Static assets
│
├── backend/                     # Node.js (TypeScript) services
│   ├── src/
│   │   ├── api/                # API endpoints
│   │   ├── services/           # Business logic services
│   │   ├── middleware/         # Express middleware
│   │   ├── models/             # Data models
│   │   └── utils/              # Utility functions
│   ├── types/                  # Shared TypeScript types
│   └── config/                 # Configuration files
│
├── agents/                      # Python agent services
│   ├── orchestration/          # Agent orchestration logic
│   │   ├── workflows/          # Workflow definitions
│   │   ├── tasks/              # Background tasks
│   │   └── chains/             # LLM chains
│   ├── services/               # Python services
│   │   ├── classifier/         # Issue classification
│   │   ├── reasoner/           # Structured reasoning
│   │   └── retrieval/          # Semantic search
│   ├── workers/                # Background workers
│   └── utils/                  # Python utilities
│
├── convex/                      # Convex schema and functions
│   ├── schema.ts               # Database schema
│   ├── functions/              # Convex functions
│   │   ├── queries.ts          # Query functions
│   │   ├── mutations.ts        # Mutation functions
│   │   └── actions.ts          # Action functions
│   └── vectors/                # Vector search indexes
│
├── shared/                      # Shared code across services
│   ├── types/                  # Shared TypeScript types
│   ├── schemas/                # Validation schemas
│   └── constants/              # Shared constants
│
├── infrastructure/              # IaC and deployment
│   ├── aws/                    # AWS CloudFormation/CDK
│   │   ├── ecs/                # ECS task definitions
│   │   └── lambda/             # Lambda functions
│   ├── docker/                 # Dockerfiles
│   └── ci-cd/                  # GitHub Actions workflows
│
└── docs/                        # Documentation
    ├── api/                    # API documentation
    ├── architecture/           # Architecture diagrams
    └── deployment/             # Deployment guides
```
```

### 3. Naming Patterns

**REQUIRED: Specify naming conventions.**

Define:
- Component naming (PascalCase vs camelCase)
- File naming (kebab-case, PascalCase, camelCase)
- Function/variable naming across languages
- Convex table/field naming
- Python module/class naming
- Constants naming

**Example:**
```markdown
## Naming Patterns

### Frontend (TypeScript/React)
- **Components:** PascalCase files and exports (`UserProfile.tsx`, `export const UserProfile`)
- **Hooks:** camelCase with `use` prefix (`useAuth.ts`, `useConvexQuery`)
- **Utilities:** camelCase (`formatDate.ts`, `validateEmail`)
- **Types/Interfaces:** PascalCase (`User`, `AuthState`, `WorkflowConfig`)
- **Constants:** UPPER_SNAKE_CASE (`API_BASE_URL`, `MAX_RETRIES`)

### Backend (Node.js/TypeScript)
- **Services:** PascalCase classes (`UserService`, `WorkflowEngine`)
- **API routes:** kebab-case files (`user-routes.ts`, `workflow-routes.ts`)
- **Functions:** camelCase (`getUserById`, `processWorkflow`)
- **Interfaces:** PascalCase with `I` prefix (`IUserService`, `IConfig`)

### Python (Agent Services)
- **Modules:** snake_case (`issue_classifier.py`, `workflow_orchestrator.py`)
- **Classes:** PascalCase (`WorkflowOrchestrator`, `IssueClassifier`)
- **Functions:** snake_case (`classify_issue`, `run_workflow`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_RETRY_ATTEMPTS`, `DEFAULT_MODEL`)

### Convex (Database)
- **Tables:** snake_case (`users`, `deployment_logs`, `workflow_states`)
- **Fields:** camelCase (`userId`, `createdAt`, `isActive`)
- **Indexes:** snake_case with prefix (`idx_user_email`, `idx_created_at`)
- **Functions:** camelCase (`getUser`, `createWorkflow`, `searchDeployments`)

### General
- **Environment variables:** UPPER_SNAKE_CASE (`OPENAI_API_KEY`, `AWS_REGION`)
- **Docker images:** kebab-case (`agent-orchestrator`, `background-worker`)
- **GitHub branches:** kebab-case (`feature/user-auth`, `fix/deployment-bug`)
```

### 4. UI Design

**REQUIRED: Comprehensive design specifications.**

Include:
- Design aesthetic/mood
- Color palette (specific hex codes or Tailwind colors)
- Typography (fonts, sizes, weights)
- Spacing/layout patterns
- Animations and transitions
- Component design patterns
- Responsive breakpoints

**IMPORTANT:** Refer to `.claude/skills/frontend/frontend.json` for the full design token specification. The example below reflects the project's established aesthetic.

**Example:**
```markdown
## UI Design

### Design Aesthetic
Dark, editorial sophistication with a dash of technical precision. Refined serif headlines, monospace details, muted sage green accents against deep blacks. Generous whitespace, understated elegance, no decoration without purpose. Like a beautifully typeset technical journal. Serious but not sterile, confident but not aggressive.

### Color Palette
- **Primary:** Sage green (#9CA896), hover (#B4BFB0), active (#8A9A84)
- **Secondary:** Muted olive (#6B7068)
- **Accent:** Light sage (#A8B5A1)
- **Background:** Deep black (#0A0A0A), elevated (#121212), subtle (#0F0F0F)
- **Surface:** Dark gray (#181818), hover (#1E1E1E), border (#282828)
- **Text:** Off-white (#E8E8E8), secondary (#A0A0A0), tertiary (#707070), muted (#505050)
- **Border:** Subtle (#242424), focus (#9CA896), hover (#2E2E2E)
- **Error:** Desaturated red (#D87C7C)
- **Success:** Desaturated green (#8DB88A)
- **Warning:** Desaturated amber (#D8B87C)

### Typography
- **Headings:** Playfair Display (serif), normal weight, tight line height - editorial feel
- **Body:** Inter, 1rem, 1.7 line height, #A0A0A0 color
- **Labels/UI elements:** IBM Plex Mono, 0.75rem, uppercase, 0.1em letter spacing, #707070
- **Emphasis:** Playfair Display italic for emphasis words in headlines

### Animations
- **Hover transitions:** 250ms cubic-bezier(0.25, 0.46, 0.45, 0.94)
- **Modal entry:** 400ms ease-out
- **Fast interactions:** 150ms
- **Loading states:** Pulse animation on skeleton loaders
- **Principle:** Refined, smooth transitions - nothing jumpy or dramatic

### Component Patterns
- **Buttons:** rounded-[4px], px-8 py-3.5, uppercase monospace text, sage green bg with dark text (primary) or transparent with subtle border (secondary)
- **Cards:** rounded-[8px], border #242424, bg #181818, 2rem padding, subtle shadow
- **Inputs:** rounded-[4px], border #242424, bg #121212, focus border #9CA896
- **Labels:** IBM Plex Mono uppercase, wide letter spacing, #707070
- **Navigation:** Transparent with backdrop-blur, subtle bottom border
- **Modals:** backdrop-blur-[16px], centered with max-w-lg

### Responsive Design
- **Mobile-first:** Default styles for mobile (< 640px)
- **Tablet:** md: breakpoint (768px+)
- **Desktop:** lg: breakpoint (1024px+)
- **Wide:** xl: breakpoint (1280px+), max content width 1280px
```

### 5. Key Features and User Flow

**REQUIRED: Detailed screen-by-screen breakdown.**

Include:
- What each screen contains
- Onboarding flow (if applicable)
- Navigation between screens
- User journey maps
- Screen states (loading, error, empty, success)
- AI/Agent interactions (if applicable)

**Example:**
```markdown
## Key Features and User Flow

### Onboarding Flow
1. **Landing Page**
   - Hero section with value proposition
   - CTA button: "Get Started"
   - Preview of key features
   
2. **Sign Up Screen**
   - Email + password form
   - Or: Social auth (Google, GitHub)
   - Link to sign in for existing users
   - → On success: Navigate to profile setup

3. **Profile Setup**
   - Name input
   - Profile photo upload (optional)
   - Bio/description (optional)
   - → On complete: Navigate to dashboard

### Main App Screens

#### Dashboard (/)
- **Header:** Logo, user menu, notifications
- **Sidebar:** Navigation links
- **Main area:** 
  - Welcome message
  - Recent activity cards
  - Quick actions (create new task, etc.)
  - Stats overview
  - AI suggestions (powered by GPT-4.1)
- **Navigation:** Links to Tasks, Projects, Settings

#### Task List (/tasks)
- **Filter bar:** Priority, status, search
- **Task cards:** Title, description, priority badge, due date
- **AI indicator:** Shows if task was auto-classified
- **Actions:** Edit, delete, mark complete
- **Create button:** Opens task creation modal
- **Navigation:** Click task → Task detail view

### AI/Agent Interactions

#### Intelligent Classification
- **Trigger:** User creates new task
- **Process:** 
  1. Task sent to Python classification service
  2. GPT-4.1 analyzes and categorizes
  3. Suggested priority/category returned
  4. User can accept or override
- **Response time:** < 2 seconds

#### Workflow Automation
- **Trigger:** User initiates automated workflow
- **Process:**
  1. Workflow orchestrator (Python) receives request
  2. Retrieves relevant context from Convex vector search
  3. GPT-4.1 performs structured reasoning
  4. Background workers execute steps
  5. Real-time updates via Convex
- **User feedback:** Progress bar with step-by-step updates

### Screen States
- **Loading:** Skeleton loaders for all content areas
- **AI Processing:** Animated spinner with "AI analyzing..." message
- **Empty:** Friendly message + illustration + CTA
- **Error:** Error message + retry button + support link
- **Success:** Confirmation toast notification (3s duration)
```

### 6. Backend / Data Schema

**REQUIRED: Complete database design.**

Include:
- All Convex tables with fields and types
- Relationships between tables
- Indexes for performance
- Vector indexes for semantic search
- Real-time subscriptions
- Authentication/authorization

**Example:**
```markdown
## Backend / Data Schema

### Convex Schema

#### users
```typescript
export const users = defineTable({
  clerkId: v.string(),           // Clerk user ID (or auth provider)
  email: v.string(),
  displayName: v.string(),
  avatarUrl: v.optional(v.string()),
  bio: v.optional(v.string()),
  role: v.union(v.literal("user"), v.literal("admin")),
  createdAt: v.number(),         // Unix timestamp
  updatedAt: v.number(),
})
  .index("by_clerk_id", ["clerkId"])
  .index("by_email", ["email"]);
```

#### tasks
```typescript
export const tasks = defineTable({
  userId: v.id("users"),
  title: v.string(),
  description: v.optional(v.string()),
  priority: v.union(
    v.literal("high"),
    v.literal("medium"),
    v.literal("low")
  ),
  status: v.union(
    v.literal("todo"),
    v.literal("in_progress"),
    v.literal("done")
  ),
  category: v.optional(v.string()),
  aiClassified: v.boolean(),     // Was this auto-classified by AI?
  dueDate: v.optional(v.number()),
  createdAt: v.number(),
  updatedAt: v.number(),
})
  .index("by_user", ["userId"])
  .index("by_status", ["status"])
  .index("by_created_at", ["createdAt"])
  .index("by_user_and_status", ["userId", "status"]);
```

#### deployment_logs
```typescript
export const deploymentLogs = defineTable({
  userId: v.id("users"),
  workflowId: v.string(),
  action: v.string(),
  status: v.union(
    v.literal("pending"),
    v.literal("running"),
    v.literal("completed"),
    v.literal("failed")
  ),
  input: v.any(),                // Workflow input data
  output: v.optional(v.any()),   // Workflow output
  error: v.optional(v.string()),
  aiDecision: v.optional(v.object({
    reasoning: v.string(),
    confidence: v.number(),
    model: v.string(),
  })),
  embedding: v.optional(v.array(v.float64())), // For vector search
  duration: v.optional(v.number()),
  createdAt: v.number(),
})
  .index("by_user", ["userId"])
  .index("by_workflow", ["workflowId"])
  .index("by_status", ["status"])
  .vectorIndex("by_embedding", {
    vectorField: "embedding",
    dimensions: 1536,              // OpenAI embedding dimension
    filterFields: ["userId"],
  });
```

#### workflow_states
```typescript
export const workflowStates = defineTable({
  userId: v.id("users"),
  workflowId: v.string(),
  currentStep: v.string(),
  steps: v.array(v.object({
    id: v.string(),
    name: v.string(),
    status: v.string(),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
  })),
  metadata: v.any(),
  createdAt: v.number(),
  updatedAt: v.number(),
})
  .index("by_user", ["userId"])
  .index("by_workflow", ["workflowId"]);
```

### Convex Functions

**Queries:**
```typescript
// frontend/lib/convex/queries.ts
export const getTasks = query({
  args: { status: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) throw new Error("Unauthorized");
    
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerk_id", q => q.eq("clerkId", identity.subject))
      .first();
    
    if (!user) throw new Error("User not found");
    
    let query = ctx.db.query("tasks").withIndex("by_user", q => q.eq("userId", user._id));
    
    if (args.status) {
      query = query.filter(q => q.eq(q.field("status"), args.status));
    }
    
    return await query.collect();
  },
});
```

**Mutations:**
```typescript
export const createTask = mutation({
  args: {
    title: v.string(),
    description: v.optional(v.string()),
    priority: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) throw new Error("Unauthorized");
    
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerk_id", q => q.eq("clerkId", identity.subject))
      .first();
    
    const taskId = await ctx.db.insert("tasks", {
      userId: user._id,
      title: args.title,
      description: args.description,
      priority: args.priority || "medium",
      status: "todo",
      aiClassified: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    
    // Trigger AI classification via action
    await ctx.scheduler.runAfter(0, internal.actions.classifyTask, {
      taskId,
    });
    
    return taskId;
  },
});
```

**Actions (for AI/external calls):**
```typescript
export const classifyTask = internalAction({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.runQuery(internal.queries.getTaskById, {
      taskId: args.taskId,
    });
    
    // Call Python classification service
    const classification = await fetch("http://classifier-service/classify", {
      method: "POST",
      body: JSON.stringify({ 
        title: task.title, 
        description: task.description 
      }),
    }).then(r => r.json());
    
    // Update task with AI classification
    await ctx.runMutation(internal.mutations.updateTaskClassification, {
      taskId: args.taskId,
      category: classification.category,
      priority: classification.priority,
      aiClassified: true,
    });
  },
});
```

### Vector Search Implementation

**Semantic Retrieval for Prior Decisions:**
```typescript
export const searchSimilarDeployments = action({
  args: { query: v.string(), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    // Get embedding from OpenAI
    const embedding = await openai.embeddings.create({
      model: "text-embedding-3-small",
      input: args.query,
    });
    
    // Search Convex vector index
    const results = await ctx.vectorSearch("deployment_logs", "by_embedding", {
      vector: embedding.data[0].embedding,
      limit: args.limit || 10,
      filter: q => q.eq(q.field("status"), "completed"),
    });
    
    return results;
  },
});
```

### Real-time Subscriptions

**Client-side usage:**
```typescript
// In React component
const tasks = useQuery(api.queries.getTasks, { status: "in_progress" });
// Automatically updates when data changes in Convex
```

### Authentication/Authorization

**Convex + Clerk Integration:**
- Clerk handles authentication
- Convex queries/mutations verify identity via `ctx.auth.getUserIdentity()`
- Row-level security enforced in queries (filter by userId)
- No direct database access without authentication
```

### 7. Goals

Specific, measurable objectives (bullet list).

**Example:**
```markdown
## Goals

- Allow users to create and manage tasks with AI-powered classification
- Provide real-time collaboration through Convex subscriptions
- Enable semantic search over deployment history using vector embeddings
- Achieve < 2s page load time on dashboard
- Support 1000+ concurrent users with real-time sync
- AI classification accuracy > 85% for task categorization
- Workflow automation reduces manual steps by 60%
```

### 8. User Stories

Each story needs:
- **Title:** Short descriptive name
- **Description:** "As a [user], I want [feature] so that [benefit]"
- **Acceptance Criteria:** Verifiable checklist of what "done" means

Each story should be small enough to implement in one focused session.

**Format:**
```markdown
### US-001: [Title]

**Description:** As a [user], I want [feature] so that [benefit].

**Acceptance Criteria:**
- [ ] Specific verifiable criterion
- [ ] Another criterion
- [ ] Typecheck/lint passes
- [ ] **[UI stories only]** Verify in browser using dev-browser skill
- [ ] **[AI stories only]** Test with sample inputs, verify accuracy > threshold
```

**Important:** 
- Acceptance criteria must be verifiable, not vague. "Works correctly" is bad. "Button shows confirmation dialog before deleting" is good.
- **For any story with UI changes:** Always include "Verify in browser using dev-browser skill" as acceptance criteria.
- **For any story with AI/LLM features:** Include specific test cases and accuracy thresholds.

### 9. Functional Requirements

Numbered list of specific functionalities:
- "FR-1: The system must allow users to..."
- "FR-2: When a user clicks X, the system must..."
- "FR-3: The AI classification service must..."
- "FR-4: Vector search must return results in..."

Be explicit and unambiguous.

### 10. Constraints

**REQUIRED: Guardrails to keep the project focused.**

Include:
- Time constraints (if any)
- Technology constraints (must use X, cannot use Y)
- Scope constraints (MVP vs full version)
- Resource constraints (team size, budget)
- Performance constraints (page load time, response time)
- AI/LLM constraints (model costs, latency)

**Example:**
```markdown
## Constraints

### Scope Constraints
- **MVP Focus:** Build only core task management features with AI classification
- **No mobile app:** Web-only for initial release
- **Single user mode:** No team/collaboration features in v1

### Technology Constraints
- **Must use:** Next.js 14+, Node.js 20+, Python 3.11+, Convex, OpenAI GPT-4.1
- **Cannot use:** Alternative databases, custom auth (use Clerk)
- **Preferred:** Functional components with hooks, async/await for Python

### Performance Constraints
- **Page load:** < 2 seconds on 3G connection
- **API response:** < 200ms for standard queries (excluding AI calls)
- **AI classification:** < 3 seconds per task
- **Real-time latency:** < 500ms for Convex updates
- **Vector search:** < 1 second for top 10 results

### Resource Constraints
- **Timeline:** 6 weeks to MVP
- **Team size:** 2-3 developers
- **Budget:** 
  - Vercel Pro tier
  - Convex Pro tier
  - AWS free tier + minimal ECS costs
  - OpenAI API budget: $500/month initial

### AI/LLM Constraints
- **Model costs:** Must stay under $500/month initially
- **Rate limits:** Respect OpenAI rate limits (tier-based)
- **Fallback:** Graceful degradation if AI service unavailable
- **Caching:** Cache embeddings and common classifications

### Design Constraints
- **Responsive required:** Must work on mobile, tablet, desktop
- **Accessibility:** WCAG 2.1 AA compliance minimum
- **Browser support:** Latest 2 versions of Chrome, Firefox, Safari, Edge
```

### 11. Security

**REQUIRED: Security measures and best practices.**

Include:
- Authentication strategy
- Where/how passwords are stored
- API key management
- Rate limiting
- Data encryption
- CORS policies
- Input validation

**Example:**
```markdown
## Security

### Authentication
- **Provider:** Clerk (handles password hashing, session management)
- **Password requirements:** Min 8 characters, complexity enforced by Clerk
- **Session management:** JWT tokens via Clerk, secure httpOnly cookies
- **Password storage:** NEVER stored in frontend or backend, handled entirely by Clerk

### API Keys & Secrets
- **Environment variables:**
  - `NEXT_PUBLIC_CONVEX_URL` - Safe to expose in frontend
  - `CONVEX_DEPLOY_KEY` - Server-side only, for deployments
  - `OPENAI_API_KEY` - Server-side only (Python services)
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - Server-side only
  - `CLERK_SECRET_KEY` - Server-side only
- **Storage:** All secrets in environment variables, never commit to git
- **Rotation:** API keys rotated quarterly, automated via AWS Secrets Manager

### Rate Limiting
- **API routes:** 
  - Read operations: 100 requests/min per user
  - Write operations: 20 requests/min per user
  - AI operations: 10 requests/min per user (prevent abuse)
- **Convex functions:** Built-in rate limiting via Convex quotas
- **OpenAI calls:** Track usage, implement circuit breaker if limits approached

### Data Encryption
- **In transit:** All API calls over HTTPS only (enforced by Vercel/AWS)
- **At rest:** Convex encrypts data at rest by default
- **Sensitive fields:** Additional encryption for any PII if added later
- **Vector embeddings:** Not considered sensitive, but access-controlled

### Input Validation
- **Frontend:** Validate all inputs before submission (prevent XSS)
- **Backend:** Zod schemas for API validation
- **Python services:** Pydantic models for data validation
- **Convex:** Strict type checking via validators
- **Sanitization:** Sanitize user-generated content before AI processing

### CORS
- **Allowed origins:** 
  - Production: `https://yourdomain.com`
  - Preview: `*.vercel.app`
  - Development: `http://localhost:3000`
- **Methods:** GET, POST, PUT, DELETE (no OPTIONS pre-flight caching)
- **Headers:** Restrict to necessary headers only

### Row Level Security
- **Convex queries:** Always filter by authenticated user ID
- **No direct access:** Users can only access their own data
- **Admin access:** Separate admin-only functions with role checks

### AI/LLM Security
- **Prompt injection:** Sanitize user inputs before sending to OpenAI
- **Output validation:** Validate AI responses before storing/displaying
- **Cost protection:** Monitor API usage, kill switch if budget exceeded
- **Data retention:** Do not log user data in OpenAI calls (zero retention)

### Additional Measures
- **Content Security Policy (CSP):** Prevent XSS attacks
- **HTTP headers:** Vercel automatic security headers
- **Audit logging:** Log all sensitive operations (Convex tables)
- **Regular updates:** Dependabot for dependency updates
- **Secrets scanning:** GitHub secret scanning enabled
```

### 12. Non-Goals (Out of Scope)

What this feature will NOT include. Critical for managing scope.

### 13. Design Considerations (Optional)

- UI/UX requirements not covered in UI Design section
- Link to mockups if available
- Relevant existing components to reuse

### 14. Technical Considerations (Optional)

- Known constraints or dependencies
- Integration points with existing systems
- Performance requirements not covered in Constraints
- AI model selection rationale
- Convex schema migration strategy

### 15. Success Metrics

How will success be measured?
- "Reduce time to complete X by 50%"
- "Increase conversion rate by 10%"
- "Achieve 95% user satisfaction in onboarding"
- "AI classification accuracy > 85%"
- "Vector search recall > 90% for top 10 results"

### 16. Open Questions

Remaining questions or areas needing clarification.

---

## Writing for Junior Developers

The PRD reader may be a junior developer or AI agent. Therefore:

- Be explicit and unambiguous
- Avoid jargon or explain it
- Provide enough detail to understand purpose and core logic
- Number requirements for easy reference
- Use concrete examples where helpful
- Explain AI/LLM integration points clearly

---

## Output

- **Format:** Markdown (`.md`)
- **Location:** `tasks/`
- **Filename:** `prd-[feature-name].md` (kebab-case)

---

## Checklist

Before saving the PRD:

- [ ] Asked clarifying questions with lettered options
- [ ] Incorporated user's answers
- [ ] **Product Overview** section completed (1 paragraph with full tech stack)
- [ ] **File Structure** section defined (frontend, backend, agents, convex, infra)
- [ ] **Naming Patterns** section specified (TypeScript, Python, Convex conventions)
- [ ] **UI Design** section comprehensive (colors, typography, animations)
- [ ] **Key Features and User Flow** section detailed (screens + AI interactions)
- [ ] **Backend/Data Schema** section complete (Convex schema, vector indexes, RLS)
- [ ] **Constraints** section defined (including AI/LLM constraints)
- [ ] **Security** section thorough (including AI security considerations)
- [ ] User stories include AI acceptance criteria where applicable
- [ ] Functional requirements are numbered and unambiguous
- [ ] Non-goals section defines clear boundaries
- [ ] Saved to `tasks/prd-[feature-name].md`