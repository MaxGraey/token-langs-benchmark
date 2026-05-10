import { serve } from "@hono/node-server";
import { Hono } from "hono";

const app = new Hono();
const users = new Map<number, { id: number; name: string }>();

app.get("/users", c => c.json([...users.values()]));

app.get("/users/:id", c => {
  const user = users.get(Number(c.req.param("id")));
  return user ? c.json(user) : c.notFound();
});

app.post("/users", async c => {
  const body = await c.req.json();
  const user = { id: users.size + 1, name: String(body.name) };
  users.set(user.id, user);
  return c.json(user, 201);
});

serve({ fetch: app.fetch, port: 3000 });
