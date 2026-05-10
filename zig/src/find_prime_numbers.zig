const std = @import("std");

fn isPrime(n: u64) bool {
    if (n < 2) return false;
    var d: u64 = 2;
    while (d * d <= n) : (d += 1) {
        if (n % d == 0) return false;
    }
    return true;
}

pub fn main() !void {
    var out = std.io.getStdOut().writer();
    try out.writeAll("[");
    var first = true;
    for (2..101) |n| {
        if (!isPrime(n)) continue;
        if (!first) try out.writeAll(", ");
        first = false;
        try out.print("{}", .{n});
    }
    try out.writeAll("]\n");
}
