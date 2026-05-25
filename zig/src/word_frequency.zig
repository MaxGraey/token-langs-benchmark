const std = @import("std");

const Entry = struct {
    word: []const u8,
    count: u32,
};

fn lessThan(_: void, a: Entry, b: Entry) bool {
    if (a.count != b.count) return a.count > b.count;
    return std.mem.order(u8, a.word, b.word) == .lt;
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();
    const text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.";
    var counts = std.StringHashMap(u32).init(allocator);
    defer counts.deinit();

    var words = std.mem.tokenizeAny(u8, text, " .,!?:;\n\t");
    while (words.next()) |raw| {
        const word = try std.ascii.allocLowerString(allocator, raw);
        const gop = try counts.getOrPut(word);
        if (gop.found_existing) {
            allocator.free(word);
        } else {
            gop.value_ptr.* = 0;
        }
        gop.value_ptr.* += 1;
    }

    var entries = std.ArrayList(Entry).init(allocator);
    defer entries.deinit();
    var it = counts.iterator();
    while (it.next()) |entry| try entries.append(.{ .word = entry.key_ptr.*, .count = entry.value_ptr.* });
    std.mem.sort(Entry, entries.items, {}, lessThan);

    for (entries.items[0..@min(entries.items.len, 5)]) |entry| {
        std.debug.print("{s}: {}\n", .{ entry.word, entry.count });
    }
}
