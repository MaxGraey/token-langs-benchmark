import { serve } from "@hono/node-server"
import { Hono } from "hono"

type User = {
  id: number
  name: string
}

const app = new Hono()
const users = new Map<number, User>()

app.get("/users", ctx => ctx.json([...users.values()]))

app.get("/users/:id", ctx => {
  const user = users.get(Number(ctx.req.param("id")))
  return user ? ctx.json(user) : ctx.notFound()
})

app.post("/users", async ctx => {
  const body = await ctx.req.json()
  const id = users.size + 1
  const user = {
    id,
    name: String(body.name)
  }
  users.set(id, user)
  return ctx.json(user, 201)
})

serve({ fetch: app.fetch, port: 3000 })
