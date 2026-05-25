const std = @import("std");
const httpz = @import("httpz");

const User = struct {
    id: u64,
    name: []const u8,
};

const Store = struct {
    allocator: std.mem.Allocator,
    users: std.AutoHashMap(u64, []const u8),

    fn init(allocator: std.mem.Allocator) Store {
        return .{ .allocator = allocator, .users = std.AutoHashMap(u64, []const u8).init(allocator) };
    }

    fn deinit(self: *Store) void {
        var it = self.users.valueIterator();
        while (it.next()) |name| self.allocator.free(name.*);
        self.users.deinit();
    }
};

fn allUsers(store: *Store, _: *httpz.Request, res: *httpz.Response) !void {
    var items = std.ArrayList(User).init(store.allocator);
    defer items.deinit();

    var it = store.users.iterator();
    while (it.next()) |entry| {
        try items.append(.{ .id = entry.key_ptr.*, .name = entry.value_ptr.* });
    }
    try res.json(items.items, .{});
}

fn getUser(store: *Store, req: *httpz.Request, res: *httpz.Response) !void {
    const id = try std.fmt.parseInt(u64, req.param("id").?, 10);
    const name = store.users.get(id) orelse {
        res.status = 404;
        return;
    };
    try res.json(User{ .id = id, .name = name }, .{});
}

fn createUser(store: *Store, req: *httpz.Request, res: *httpz.Response) !void {
    const body = try req.json(struct { name: []const u8 }, .{});
    const id = store.users.count() + 1;
    try store.users.put(id, try store.allocator.dupe(u8, body.name));
    res.status = 201;
    try res.json(User{ .id = id, .name = body.name }, .{});
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    var store = Store.init(gpa.allocator());
    defer store.deinit();

    var server = try httpz.Server(*Store).init(gpa.allocator(), .{ .port = 3000 }, &store);
    defer server.deinit();

    server.router().get("/users", allUsers, .{});
    server.router().get("/users/:id", getUser, .{});
    server.router().post("/users", createUser, .{});
    try server.listen();
}
