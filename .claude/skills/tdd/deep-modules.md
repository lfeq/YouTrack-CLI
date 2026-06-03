# Deep Modules

**Deep modules** feature a "small interface + lots of implementation." They present users with few methods and straightforward parameters while concealing complex logic internally. This design minimizes cognitive burden on callers.

**Shallow modules** exhibit the opposite pattern: "large interface + little implementation." They expose many methods and complex parameters while delegating work elsewhere, creating unnecessary complexity for users.

The design philosophy suggests developers should pursue these improvements:

- Reduce the method count in your interface
- Streamline parameter complexity
- Encapsulate more logic within the module itself

This approach aligns with the principle that well-designed interfaces shield users from implementation details while maximizing the value hidden beneath the surface.
