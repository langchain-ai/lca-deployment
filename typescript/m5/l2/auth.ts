import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

// Stand-in for a real user database. Do not use hardcoded tokens in production.
const VALID_TOKENS: Record<string, { id: string; name: string }> = {
  "alice-token": { id: "user1", name: "Alice" },
  "bob-token":   { id: "user2", name: "Bob" },
};

export const auth = new Auth().authenticate(async (request) => {
  const authorization = request.headers.get("Authorization");
  if (!authorization) {
    throw new HTTPException(401, { message: "Missing token" });
  }
  const [scheme, token] = authorization.split(" ");
  if (scheme?.toLowerCase() !== "bearer" || !token || !VALID_TOKENS[token]) {
    throw new HTTPException(401, { message: "Invalid token" });
  }
  return { identity: VALID_TOKENS[token].id, permissions: [] };
});
