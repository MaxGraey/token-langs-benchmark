const std = @import("std");

const Json = union(enum) {
    null,
    bool: bool,
    number: f64,
    string: []const u8,
    array: []Json,
    object: []Field,
};

const Field = struct {
    key: []const u8,
    value: Json,
};

const Parser = struct {
    allocator: std.mem.Allocator,
    input: []const u8,
    pos: usize = 0,

    fn parse(self: *Parser) !Json {
        const result = try self.value();
        self.ws();
        if (self.pos != self.input.len) return error.TrailingInput;
        return result;
    }

    fn value(self: *Parser) !Json {
        self.ws();
        return switch (self.peek() orelse return error.ExpectedValue) {
            'n' => try self.literal("null", .null),
            't' => try self.literal("true", .{ .bool = true }),
            'f' => try self.literal("false", .{ .bool = false }),
            '"' => .{ .string = try self.string() },
            '[' => .{ .array = try self.array() },
            '{' => .{ .object = try self.object() },
            '-', '0'...'9' => .{ .number = try self.number() },
            else => error.ExpectedValue,
        };
    }

    fn literal(self: *Parser, word: []const u8, value: Json) !Json {
        if (!std.mem.startsWith(u8, self.input[self.pos..], word)) return error.BadLiteral;
        self.pos += word.len;
        return value;
    }

    fn string(self: *Parser) ![]const u8 {
        try self.bump('"');
        var out = std.ArrayList(u8).init(self.allocator);
        errdefer out.deinit();

        while (self.next()) |ch| switch (ch) {
            '"' => return try out.toOwnedSlice(),
            '\\' => try out.append(switch (self.next() orelse return error.BadEscape) {
                '"' => '"',
                '\\' => '\\',
                '/' => '/',
                'b' => 8,
                'f' => 12,
                'n' => '\n',
                'r' => '\r',
                't' => '\t',
                else => return error.BadEscape,
            }),
            else => try out.append(ch),
        };
        return error.UnterminatedString;
    }

    fn number(self: *Parser) !f64 {
        const start = self.pos;
        while (self.peek()) |ch| {
            switch (ch) {
                '-', '+', '.', 'e', 'E', '0'...'9' => self.pos += 1,
                else => break,
            }
        }
        return std.fmt.parseFloat(f64, self.input[start..self.pos]);
    }

    fn array(self: *Parser) ![]Json {
        try self.bump('[');
        var items = std.ArrayList(Json).init(self.allocator);
        errdefer items.deinit();

        while (true) {
            self.ws();
            if (self.eat(']')) return try items.toOwnedSlice();
            try items.append(try self.value());
            self.ws();
            if (!self.eat(',')) {
                try self.bump(']');
                return try items.toOwnedSlice();
            }
        }
    }

    fn object(self: *Parser) ![]Field {
        try self.bump('{');
        var fields = std.ArrayList(Field).init(self.allocator);
        errdefer fields.deinit();

        while (true) {
            self.ws();
            if (self.eat('}')) return try fields.toOwnedSlice();
            const key = try self.string();
            self.ws();
            try self.bump(':');
            try fields.append(.{ .key = key, .value = try self.value() });
            self.ws();
            if (!self.eat(',')) {
                try self.bump('}');
                return try fields.toOwnedSlice();
            }
        }
    }

    fn ws(self: *Parser) void {
        while (self.peek()) |ch| switch (ch) {
            ' ', '\n', '\r', '\t' => self.pos += 1,
            else => return,
        };
    }

    fn bump(self: *Parser, expected: u8) !void {
        if (!self.eat(expected)) return error.UnexpectedChar;
    }

    fn eat(self: *Parser, expected: u8) bool {
        if (self.peek() == expected) {
            self.pos += 1;
            return true;
        }
        return false;
    }

    fn next(self: *Parser) ?u8 {
        const ch = self.peek() orelse return null;
        self.pos += 1;
        return ch;
    }

    fn peek(self: *Parser) ?u8 {
        if (self.pos < self.input.len) return self.input[self.pos];
        return null;
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    var parser = Parser{ .allocator = gpa.allocator(), .input = "{\"name\":\"Ada\",\"scores\":[1,2,3],\"ok\":true}" };
    const value = try parser.parse();
    std.debug.print("{any}\n", .{value});
}
