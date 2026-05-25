const std = @import("std");

fn isPrime(n: usize) bool {
    const limit = std.math.sqrt(n);
    var d: usize = 2;
    while (d <= limit) : (d += 1) {
        if (n % d == 0) return false;
    }
    return true;
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var primes = std.ArrayList(usize).init(allocator);
    defer primes.deinit();

    for (2..101) |n| {
        if (isPrime(n)) try primes.append(n);
    }

    std.debug.print("{any}\n", .{primes.items});
}
