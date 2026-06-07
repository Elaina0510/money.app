import { vi } from 'vitest'

// Store reference to the guard function
let routeLeaveGuard = null

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: vi.fn(),
    push: vi.fn(),
  }),
  useRoute: () => ({
    params: {},
  }),
  onBeforeRouteLeave: vi.fn((guard) => {
    routeLeaveGuard = guard
  }),
}))

// Export for test access
export { routeLeaveGuard }
