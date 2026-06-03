# Interface Design for Testability

Three core principles for creating testable interfaces:

**Dependency Injection**: Rather than instantiating dependencies internally, "Accept dependencies, don't create them." This allows tests to inject mock implementations. The example contrasts a testable function that accepts a `paymentGateway` parameter versus one that creates a `StripeGateway` internally.

**Functional Returns**: Interfaces should "Return results, don't produce side effects." A function computing a discount should return the calculated value rather than mutating the input object directly, making behavior easier to verify in tests.

**Minimal Interface Surface**: Limiting the number of methods and parameters reduces testing complexity. Fewer public members mean fewer test scenarios to cover, and simpler parameter lists require less elaborate test setup.

These principles collectively promote separation of concerns and make behavior more observable and verifiable during testing.
