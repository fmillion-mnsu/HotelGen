# HotelGen Migration Guide: Python to C# (.NET Core)

This document provides guidance for migrating the HotelGen simulation project from Python to C# with .NET Core.

## Table of Contents

1. [Data Classes Migration](#1-data-classes-migration)
2. [Pickle Alternatives](#2-pickle-alternatives)
3. [Progress Tracking (tqdm replacement)](#3-progress-tracking-tqdm-replacement)
4. [Database Bulk Inserts](#4-database-bulk-inserts)
5. [Python Pattern Translations](#5-python-pattern-translations)
6. [Architecture Recommendations](#6-architecture-recommendations)
7. [Gotchas and Pitfalls](#7-gotchas-and-pitfalls)

---

## 1. Data Classes Migration

### Python Dataclasses → C# Records

Python dataclasses map naturally to C# records (introduced in C# 9). Records provide immutability, value equality, and concise syntax.

### Current Python Models

```python
@dataclass
class RoomInfo:
    count: int
    price: float

@dataclass
class Hotel:
    name: str
    street: str
    city: str
    state: str          # 2 char max
    zip: str            # 10 char max
    email: str
    website: str
    phone: str          # 12 char max
    type: str           # 'resort', 'hotel', or 'motel'
    tourist_region: Optional[str]
    rooms: dict[str, RoomInfo]
    base_price: float
    resort_fee: float
    id: Optional[int] = None

@dataclass
class Customer:
    fname: str
    lname: str
    street: str
    city: str
    state: str
    zip: str
    email: str
    phone: str
    type: str           # 'rare_leisure', 'regular_leisure', etc.
    id: Optional[int] = None

@dataclass
class LineItem:
    description: str
    amount_per: float
    quantity: int

@dataclass
class Payment:
    method: str
    amount: float
    status: str         # 'APPROVED' or 'DECLINED'

@dataclass
class Transaction:
    customer_id: int
    hotel_id: int
    check_in_date: str
    check_out_date: datetime
    line_items: list[LineItem]
    total: float
    payment: Payment
    id: Optional[int] = None
```

### Equivalent C# Records

```csharp
namespace HotelGen.Models;

public record RoomInfo(int Count, decimal Price);

public record Hotel(
    string Name,
    string Street,
    string City,
    string State,           // MaxLength(2)
    string Zip,             // MaxLength(10)
    string Email,
    string Website,
    string Phone,           // MaxLength(12)
    HotelType Type,
    string? TouristRegion,
    Dictionary<string, RoomInfo> Rooms,
    decimal BasePrice,
    decimal ResortFee,
    int? Id = null
);

public record Customer(
    string FirstName,
    string LastName,
    string Street,
    string City,
    string State,
    string Zip,
    string Email,
    string Phone,
    CustomerType Type,
    int? Id = null
);

public record LineItem(string Description, decimal AmountPer, int Quantity);

public record Payment(string Method, decimal Amount, PaymentStatus Status);

public record Transaction(
    int CustomerId,
    int HotelId,
    DateOnly CheckInDate,
    DateOnly CheckOutDate,
    List<LineItem> LineItems,
    decimal Total,
    Payment Payment,
    int? Id = null
);

// Enums for type safety (optional but recommended)
public enum HotelType { Resort, Hotel, Motel }
public enum CustomerType { RareLeisure, RegularLeisure, Business, Corporate, RoadWarrior }
public enum PaymentStatus { Approved, Declined }
```

### Alternative: Mutable Classes

If you need mutability (e.g., assigning IDs after creation), use classes with `init` accessors:

```csharp
public class Hotel
{
    public required string Name { get; init; }
    public required string Street { get; init; }
    // ... other properties
    public int? Id { get; set; }  // Mutable for ID assignment
}
```

### Record Gotcha: Dictionary Equality

Records use value equality, but `Dictionary<K,V>` uses reference equality. Two hotels with identical data but different dictionary instances won't be equal:

```csharp
var rooms1 = new Dictionary<string, RoomInfo> { ["1kn"] = new(10, 100m) };
var rooms2 = new Dictionary<string, RoomInfo> { ["1kn"] = new(10, 100m) };

var hotel1 = new Hotel(..., Rooms: rooms1, ...);
var hotel2 = new Hotel(..., Rooms: rooms2, ...);

// hotel1 == hotel2 is FALSE due to dictionary reference inequality
```

If equality matters, consider using `ImmutableDictionary` or implementing custom equality.

---

## 2. Pickle Alternatives

### Why Not Pickle?

- Pickle is Python-specific and cannot be read by C#
- Security concerns with untrusted pickle files
- No cross-platform compatibility

### Option A: System.Text.Json (Recommended)

Built into .NET, fast, and produces human-readable output.

```csharp
using System.Text.Json;
using System.Text.Json.Serialization;

public class SimulationStateSerializer
{
    private static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,  // Compact for large files
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter() }
    };

    public static async Task ExportAsync(SimulationState state, string path)
    {
        await using var stream = File.Create(path);
        await JsonSerializer.SerializeAsync(stream, state, Options);
    }

    public static async Task<SimulationState> ImportAsync(string path)
    {
        await using var stream = File.OpenRead(path);
        return await JsonSerializer.DeserializeAsync<SimulationState>(stream, Options)
            ?? throw new InvalidDataException("Failed to deserialize state");
    }
}
```

### Option B: MessagePack (Faster, Smaller Files)

Binary format, ~2-4x faster than JSON, smaller file sizes.

```bash
dotnet add package MessagePack
```

```csharp
using MessagePack;

[MessagePackObject]
public class SimulationState
{
    [Key(0)] public List<Hotel> Hotels { get; set; } = [];
    [Key(1)] public List<Customer> Customers { get; set; } = [];
    [Key(2)] public List<Transaction> Transactions { get; set; } = [];
    [Key(3)] public Dictionary<string, object?> GenParams { get; set; } = [];
}

// Serialize
var bytes = MessagePackSerializer.Serialize(state);
await File.WriteAllBytesAsync("state.msgpack", bytes);

// Deserialize
var bytes = await File.ReadAllBytesAsync("state.msgpack");
var state = MessagePackSerializer.Deserialize<SimulationState>(bytes);
```

### Option C: MemoryPack (Fastest)

Zero-copy serialization, extremely fast but .NET-only.

```bash
dotnet add package MemoryPack
```

```csharp
using MemoryPack;

[MemoryPackable]
public partial class SimulationState { ... }

// Serialize
var bytes = MemoryPackSerializer.Serialize(state);

// Deserialize
var state = MemoryPackSerializer.Deserialize<SimulationState>(bytes);
```

### Performance Comparison (Approximate)

| Format      | Serialize | Deserialize | File Size | Human Readable |
|-------------|-----------|-------------|-----------|----------------|
| JSON        | 1x        | 1x          | 1x        | Yes            |
| MessagePack | 2-3x      | 2-4x        | 0.5-0.7x  | No             |
| MemoryPack  | 5-10x     | 5-10x       | 0.4-0.6x  | No             |

### Recommendation

Start with **System.Text.Json** for compatibility and debugging, then switch to **MessagePack** if serialization becomes a bottleneck.

---

## 3. Progress Tracking (tqdm Replacement)

### Option A: Spectre.Console (Recommended)

Rich console UI with progress bars, tables, and more.

```bash
dotnet add package Spectre.Console
```

```csharp
using Spectre.Console;

// Simple progress bar
await AnsiConsole.Progress()
    .StartAsync(async ctx =>
    {
        var task = ctx.AddTask("[green]Generating hotels[/]");
        task.MaxValue = hotelCount;

        foreach (var hotel in GenerateHotels())
        {
            // Process hotel...
            task.Increment(1);
        }
    });

// Multiple concurrent progress bars
await AnsiConsole.Progress()
    .Columns(
        new TaskDescriptionColumn(),
        new ProgressBarColumn(),
        new PercentageColumn(),
        new RemainingTimeColumn(),
        new SpinnerColumn()
    )
    .StartAsync(async ctx =>
    {
        var hotelsTask = ctx.AddTask("Generating hotels", maxValue: hotelCount);
        var customersTask = ctx.AddTask("Generating customers", maxValue: customerCount);

        // Update as work progresses
        hotelsTask.Increment(1);
    });
```

### Option B: ShellProgressBar

Simpler API, closer to tqdm's feel.

```bash
dotnet add package ShellProgressBar
```

```csharp
using ShellProgressBar;

var options = new ProgressBarOptions
{
    ForegroundColor = ConsoleColor.Green,
    ProgressCharacter = '─',
    ShowEstimatedDuration = true
};

using var pbar = new ProgressBar(totalCount, "Generating hotels", options);
foreach (var item in items)
{
    // Process...
    pbar.Tick();
}
```

### Option C: Manual Console Progress

No dependencies, good for simple cases.

```csharp
public class ConsoleProgress : IDisposable
{
    private readonly int _total;
    private readonly string _description;
    private int _current;
    private readonly Stopwatch _sw = Stopwatch.StartNew();

    public ConsoleProgress(int total, string description)
    {
        _total = total;
        _description = description;
        Console.CursorVisible = false;
    }

    public void Tick()
    {
        _current++;
        var percent = (double)_current / _total * 100;
        var elapsed = _sw.Elapsed;
        var eta = TimeSpan.FromTicks(elapsed.Ticks * _total / _current) - elapsed;

        Console.Write($"\r{_description}: {_current}/{_total} ({percent:F1}%) ETA: {eta:mm\\:ss}  ");
    }

    public void Dispose()
    {
        Console.WriteLine();
        Console.CursorVisible = true;
    }
}
```

### Chunked Operations with Progress

Replicating the Python `chunked_executemany` pattern:

```csharp
public static async Task ChunkedInsertAsync<T>(
    IEnumerable<T> items,
    Func<IEnumerable<T>, Task> insertBatch,
    int chunkSize = 10000,
    string description = "Inserting")
{
    var itemList = items as IList<T> ?? items.ToList();
    var chunks = itemList.Chunk(chunkSize).ToList();

    using var pbar = new ProgressBar(chunks.Count, description);
    foreach (var chunk in chunks)
    {
        await insertBatch(chunk);
        pbar.Tick();
    }
}
```

---

## 4. Database Bulk Inserts

### The Problem with Entity Framework

EF Core generates individual INSERT statements, which is slow for bulk operations. Even with `AddRange()` and `SaveChanges()`, you get:

```sql
INSERT INTO Hotels (Name, ...) VALUES (@p0, ...); SELECT SCOPE_IDENTITY();
INSERT INTO Hotels (Name, ...) VALUES (@p1, ...); SELECT SCOPE_IDENTITY();
-- Repeated thousands of times
```

### Option A: SqlBulkCopy (Fastest)

`SqlBulkCopy` uses SQL Server's bulk insert protocol (TDS bulk load), which is **10-100x faster** than parameterized inserts.

```csharp
using Microsoft.Data.SqlClient;

public class BulkLoader
{
    private readonly string _connectionString;

    public async Task BulkLoadHotelsAsync(IEnumerable<Hotel> hotels)
    {
        using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();

        // Create a DataTable matching the target table structure
        var table = new DataTable();
        table.Columns.Add("id", typeof(int));
        table.Columns.Add("name", typeof(string));
        table.Columns.Add("street_address", typeof(string));
        table.Columns.Add("city", typeof(string));
        table.Columns.Add("state", typeof(string));
        table.Columns.Add("zip", typeof(string));
        table.Columns.Add("email", typeof(string));
        table.Columns.Add("website", typeof(string));
        table.Columns.Add("phone", typeof(string));

        foreach (var hotel in hotels)
        {
            table.Rows.Add(
                hotel.Id,
                hotel.Name,
                hotel.Street,
                hotel.City,
                hotel.State,
                hotel.Zip,
                hotel.Email,
                hotel.Website,
                hotel.Phone
            );
        }

        using var bulkCopy = new SqlBulkCopy(connection)
        {
            DestinationTableName = "property",
            BatchSize = 10000,
            BulkCopyTimeout = 600  // 10 minutes
        };

        // Map columns (important if column order differs)
        bulkCopy.ColumnMappings.Add("id", "id");
        bulkCopy.ColumnMappings.Add("name", "name");
        // ... add all mappings

        await bulkCopy.WriteToServerAsync(table);
    }
}
```

### Option B: SqlBulkCopy with IDataReader (Memory Efficient)

For very large datasets, avoid loading everything into a DataTable:

```csharp
public class HotelDataReader : IDataReader
{
    private readonly IEnumerator<Hotel> _enumerator;
    private static readonly string[] ColumnNames =
        ["id", "name", "street_address", "city", "state", "zip", "email", "website", "phone"];

    public HotelDataReader(IEnumerable<Hotel> hotels)
    {
        _enumerator = hotels.GetEnumerator();
    }

    public bool Read() => _enumerator.MoveNext();

    public int FieldCount => ColumnNames.Length;

    public object GetValue(int i) => i switch
    {
        0 => _enumerator.Current.Id ?? (object)DBNull.Value,
        1 => _enumerator.Current.Name,
        2 => _enumerator.Current.Street,
        3 => _enumerator.Current.City,
        4 => _enumerator.Current.State,
        5 => _enumerator.Current.Zip,
        6 => _enumerator.Current.Email,
        7 => _enumerator.Current.Website,
        8 => _enumerator.Current.Phone,
        _ => throw new IndexOutOfRangeException()
    };

    // Implement remaining IDataReader members...
}

// Usage
using var reader = new HotelDataReader(hotels);
await bulkCopy.WriteToServerAsync(reader);
```

### Option C: EF Core Extensions (EFCore.BulkExtensions)

If you want to stay within EF Core:

```bash
dotnet add package EFCore.BulkExtensions
```

```csharp
using EFCore.BulkExtensions;

await context.BulkInsertAsync(hotels, new BulkConfig
{
    BatchSize = 10000,
    SetOutputIdentity = true  // Populates IDs after insert
});
```

### Option D: Dapper with TVP (Table-Valued Parameters)

Good middle ground between raw SQL and ORM:

```bash
dotnet add package Dapper
```

```csharp
// Create a SQL Server User-Defined Table Type first:
// CREATE TYPE dbo.HotelTableType AS TABLE (
//     id INT, name NVARCHAR(255), ...
// );

using Dapper;

var tvp = new DataTable();
// ... populate tvp

var parameters = new DynamicParameters();
parameters.Add("@hotels", tvp.AsTableValuedParameter("dbo.HotelTableType"));

await connection.ExecuteAsync(
    "INSERT INTO property SELECT * FROM @hotels",
    parameters
);
```

### Performance Comparison

| Method                  | 10K rows | 100K rows | 1M rows  |
|-------------------------|----------|-----------|----------|
| EF Core (individual)    | ~30s     | ~5 min    | ~50 min  |
| EF Core (AddRange)      | ~10s     | ~2 min    | ~20 min  |
| EFCore.BulkExtensions   | ~1s      | ~8s       | ~80s     |
| SqlBulkCopy             | ~0.3s    | ~2s       | ~20s     |

### Disabling Constraints During Bulk Load

Replicate the Python pattern of disabling foreign keys:

```csharp
public async Task DisableForeignKeysAsync(SqlConnection connection)
{
    const string query = """
        SELECT
            OBJECT_NAME(parent_object_id) AS TableName,
            name AS ConstraintName
        FROM sys.foreign_keys
        WHERE is_disabled = 0
        """;

    var constraints = await connection.QueryAsync<(string Table, string Constraint)>(query);

    foreach (var (table, constraint) in constraints)
    {
        await connection.ExecuteAsync(
            $"ALTER TABLE [{table}] NOCHECK CONSTRAINT [{constraint}]"
        );
    }
}

public async Task EnableForeignKeysAsync(SqlConnection connection)
{
    // Re-enable with validation
    foreach (var (table, constraint) in _disabledConstraints)
    {
        await connection.ExecuteAsync(
            $"ALTER TABLE [{table}] WITH CHECK CHECK CONSTRAINT [{constraint}]"
        );
    }
}
```

---

## 5. Python Pattern Translations

### List Comprehensions → LINQ

```python
# Python
property_values = [(h.id, h.name, h.city) for h in hotels]
active_hotels = [h for h in hotels if h.type == 'resort']
```

```csharp
// C#
var propertyValues = hotels.Select(h => (h.Id, h.Name, h.City)).ToList();
var activeHotels = hotels.Where(h => h.Type == HotelType.Resort).ToList();
```

### Dictionary Comprehensions → ToDictionary

```python
# Python
room_type_cache = {code: id for id, code in cursor.fetchall()}
hotels_by_id = {h.id: h for h in hotels}
```

```csharp
// C#
var roomTypeCache = results.ToDictionary(r => r.Code, r => r.Id);
var hotelsById = hotels.ToDictionary(h => h.Id!.Value);
```

### Set Operations

```python
# Python
checked_in_ids = set(booking[0] for room in occupied.values() for booking in room)
available = [c for c in customers if c.id not in checked_in_ids]
```

```csharp
// C#
var checkedInIds = occupied.Values
    .SelectMany(room => room)
    .Select(b => b.CustomerId)
    .ToHashSet();
var available = customers.Where(c => !checkedInIds.Contains(c.Id!.Value)).ToList();
```

### Optional/None Handling

```python
# Python
value = d.get('key', default_value)
result = obj.method() if obj else None
```

```csharp
// C#
var value = d.GetValueOrDefault("key", defaultValue);
// or
d.TryGetValue("key", out var value);

var result = obj?.Method();
```

### String Formatting

```python
# Python
f"Room charge: ${price:.2f}"
"{} nights at {} per night".format(nights, rate)
```

```csharp
// C#
$"Room charge: ${price:F2}"
$"{nights} nights at {rate} per night"
// or
string.Format("{0} nights at {1} per night", nights, rate);
```

### Random Number Generation

```python
# Python
import random
rng = random.Random(seed)
value = rng.randint(1, 100)
choice = rng.choice(items)
rng.shuffle(items)
```

```csharp
// C#
var rng = new Random(seed);
var value = rng.Next(1, 101);  // Upper bound is exclusive!
var choice = items[rng.Next(items.Count)];
// or with .NET 8+
var choice = rng.GetItems(items.AsSpan(), 1)[0];
// Shuffle
items = items.OrderBy(_ => rng.Next()).ToList();
// or in-place with .NET 8+
rng.Shuffle(items.AsSpan());
```

### Date Operations

```python
# Python
from datetime import datetime, timedelta
today = datetime.now()
checkout = checkin + timedelta(days=nights)
date_str = today.strftime("%Y-%m-%d")
```

```csharp
// C#
var today = DateTime.Now;
// or DateOnly for date-only operations
var today = DateOnly.FromDateTime(DateTime.Now);
var checkout = checkin.AddDays(nights);
var dateStr = today.ToString("yyyy-MM-dd");
```

### YAML Loading

```bash
dotnet add package YamlDotNet
```

```python
# Python
from yaml import safe_load
config = safe_load(open("job.yaml"))["job"]
```

```csharp
// C#
using YamlDotNet.Serialization;

var deserializer = new DeserializerBuilder().Build();
var config = deserializer.Deserialize<JobConfig>(File.ReadAllText("job.yaml"));
```

### Global/Module-Level State → Static Classes

```python
# Python
_name_pool = None

def get_name_pool():
    global _name_pool
    if _name_pool is None:
        _name_pool = load_names()
    return _name_pool
```

```csharp
// C#
public static class NamePool
{
    private static readonly Lazy<List<string>> _names =
        new(() => LoadNames());

    public static IReadOnlyList<string> Names => _names.Value;
}
```

---

## 6. Architecture Recommendations

### Recommended Project Structure

```
HotelGen/
├── HotelGen.sln
├── src/
│   ├── HotelGen.Core/           # Models, interfaces
│   │   ├── Models/
│   │   │   ├── Hotel.cs
│   │   │   ├── Customer.cs
│   │   │   └── Transaction.cs
│   │   ├── Interfaces/
│   │   │   ├── IDataLoader.cs
│   │   │   └── ISimulationState.cs
│   │   └── HotelGen.Core.csproj
│   ├── HotelGen.Simulation/     # Generation logic
│   │   ├── Phases/
│   │   │   ├── Phase0_Parameters.cs
│   │   │   ├── Phase1_Hotels.cs
│   │   │   ├── Phase2_Customers.cs
│   │   │   └── Phase3_Prepare.cs
│   │   ├── DayProcessor.cs
│   │   ├── SimulationState.cs
│   │   └── HotelGen.Simulation.csproj
│   ├── HotelGen.Data/           # Database operations
│   │   ├── Loaders/
│   │   │   └── SqlServerLoader.cs
│   │   ├── Schema.cs
│   │   └── HotelGen.Data.csproj
│   └── HotelGen.Cli/            # Entry point
│       ├── Program.cs
│       └── HotelGen.Cli.csproj
└── tests/
    └── HotelGen.Tests/
```

### Simulation State Class

Replace the Python dictionary-based state with a typed class:

```csharp
public class SimulationState
{
    // Generated data
    public List<Hotel> Hotels { get; set; } = [];
    public List<Customer> Customers { get; set; } = [];
    public List<Transaction> Transactions { get; set; } = [];
    public List<SimulationEvent> Events { get; set; } = [];

    // Generation parameters
    public GenerationParameters GenParams { get; set; } = new();

    // Simulation state
    public Dictionary<int, Dictionary<string, List<Booking>>> OccupiedRooms { get; set; } = [];
    public Dictionary<CustomerType, HashSet<int>> OccupiedCustomers { get; set; } = [];

    // Caches (rebuilt on load, not serialized)
    [JsonIgnore]
    public Dictionary<CustomerType, List<int>> CustomersByArchetype { get; set; } = [];
    [JsonIgnore]
    public Dictionary<int, Customer> CustomersById { get; set; } = [];
    [JsonIgnore]
    public Dictionary<int, Hotel> HotelsById { get; set; } = [];

    // Progress tracking
    public DateOnly CurrentDay { get; set; }
    public int CurrentDayNum { get; set; }
    public int DaysLeft { get; set; }
    public int LastPhase { get; set; }
}
```

### Dependency Injection Setup

```csharp
// Program.cs
var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddSingleton<SimulationState>();
builder.Services.AddTransient<Phase0_Parameters>();
builder.Services.AddTransient<Phase1_Hotels>();
builder.Services.AddTransient<Phase2_Customers>();
builder.Services.AddTransient<Phase3_Prepare>();
builder.Services.AddTransient<DayProcessor>();
builder.Services.AddTransient<IDataLoader, SqlServerLoader>();
builder.Services.AddSingleton<IStateSerializer, JsonStateSerializer>();

var app = builder.Build();
await app.Services.GetRequiredService<SimulationRunner>().RunAsync();
```

### Parallel Generation (Performance Boost)

C# makes parallelism easier than Python. Generate customers in parallel:

```csharp
public List<Customer> GenerateCustomers(int count)
{
    return Enumerable.Range(0, count)
        .AsParallel()
        .WithDegreeOfParallelism(Environment.ProcessorCount)
        .Select(i => GenerateCustomer(i))
        .ToList();
}
```

Note: Ensure thread-safe random number generation:

```csharp
// Thread-local random to avoid contention
private static readonly ThreadLocal<Random> ThreadRandom =
    new(() => new Random(Interlocked.Increment(ref _seed)));

private static int _seed = Environment.TickCount;
```

---

## 7. Gotchas and Pitfalls

### 1. Random.Next() Upper Bound is Exclusive

```python
# Python: inclusive on both ends
random.randint(1, 10)  # Returns 1-10
```

```csharp
// C#: upper bound is EXCLUSIVE
rng.Next(1, 10);   // Returns 1-9
rng.Next(1, 11);   // Returns 1-10 (correct equivalent)
```

### 2. Float vs Decimal for Money

Python uses `float` for prices, but C# should use `decimal` for financial calculations:

```python
# Python (imprecise for money)
price = 99.99
```

```csharp
// C# (precise for money)
decimal price = 99.99m;  // Note the 'm' suffix
```

### 3. Dictionary Key Types

Python allows any hashable type as dictionary keys. C# dictionaries require proper `GetHashCode()` and `Equals()`:

```csharp
// If using custom types as keys, ensure they implement equality correctly
// Records handle this automatically
public record RoomTypeKey(int HotelId, string RoomType);
var occupancy = new Dictionary<RoomTypeKey, int>();
```

### 4. Null Reference Handling

C# 8+ has nullable reference types. Enable them and handle nulls explicitly:

```csharp
// In .csproj
<Nullable>enable</Nullable>
```

```csharp
// Code
string? touristRegion = hotel.TouristRegion;  // Explicitly nullable
if (touristRegion is not null)
{
    // Use touristRegion safely
}
```

### 5. String Comparison

Python strings compare by value. C# strings also compare by value, but be careful with culture:

```csharp
// Case-insensitive comparison
if (string.Equals(a, b, StringComparison.OrdinalIgnoreCase))

// For sorting
items.OrderBy(x => x.Name, StringComparer.OrdinalIgnoreCase)
```

### 6. DateTime vs DateOnly

Python's `datetime` is used for dates. C# has both `DateTime` and `DateOnly` (preferred for dates without time):

```csharp
// For check-in/check-out dates, use DateOnly
public DateOnly CheckInDate { get; set; }
public DateOnly CheckOutDate { get; set; }

// Parsing
var date = DateOnly.ParseExact("2024-01-15", "yyyy-MM-dd");
```

### 7. List Mutation During Iteration

Python allows some list mutations during iteration. C# throws `InvalidOperationException`:

```python
# Python (may work but dangerous)
for item in items:
    if should_remove(item):
        items.remove(item)
```

```csharp
// C# - use RemoveAll or iterate backwards
items.RemoveAll(item => ShouldRemove(item));

// Or iterate backwards
for (int i = items.Count - 1; i >= 0; i--)
{
    if (ShouldRemove(items[i]))
        items.RemoveAt(i);
}
```

### 8. IDENTITY_INSERT Equivalent

The Python code uses `SET IDENTITY_INSERT ON` for explicit IDs. Same in C#:

```csharp
await connection.ExecuteAsync("SET IDENTITY_INSERT property ON");
await bulkCopy.WriteToServerAsync(table);
await connection.ExecuteAsync("SET IDENTITY_INSERT property OFF");
```

But note: `SqlBulkCopy` with explicit IDs requires:
```csharp
bulkCopy.SqlRowsCopied += (sender, e) => { };  // Optional progress
// Ensure ID column is included in column mappings
```

### 9. Connection String Differences

```python
# Python pyodbc
"DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=..."
```

```csharp
// C# SqlClient
"Server=...;Database=...;User Id=...;Password=...;TrustServerCertificate=True"
```

### 10. Async All the Way

C# async is viral - once you start, continue throughout:

```csharp
// Bad - blocks thread
var result = LoadDataAsync().Result;

// Good - async all the way
var result = await LoadDataAsync();
```

### 11. IEnumerable is Lazy

Unlike Python lists, LINQ queries are lazy:

```csharp
// This doesn't execute yet!
var filtered = hotels.Where(h => h.Type == HotelType.Resort);

// Multiple enumerations = multiple executions
Console.WriteLine(filtered.Count());  // Executes query
Console.WriteLine(filtered.First());  // Executes query AGAIN

// Fix: materialize once
var filtered = hotels.Where(h => h.Type == HotelType.Resort).ToList();
```

### 12. Chunk() Method

.NET 6+ has `Chunk()` built-in:

```csharp
// Split into batches of 10000
foreach (var batch in items.Chunk(10000))
{
    await ProcessBatchAsync(batch);
}
```

---

## Summary: Recommended Migration Path

1. **Start with Models** - Convert dataclasses to records
2. **Add Serialization** - Implement JSON export/import
3. **Port Generation Logic** - Phases 0-3 with LINQ instead of comprehensions
4. **Port Simulation Loop** - Day processing with proper date handling
5. **Implement Bulk Loader** - Use SqlBulkCopy for performance
6. **Add Progress Reporting** - Spectre.Console for rich output
7. **Add CLI** - System.CommandLine for argument parsing

### NuGet Packages to Consider

```xml
<ItemGroup>
  <!-- Required -->
  <PackageReference Include="Microsoft.Data.SqlClient" Version="5.*" />

  <!-- Recommended -->
  <PackageReference Include="Spectre.Console" Version="0.49.*" />
  <PackageReference Include="YamlDotNet" Version="16.*" />
  <PackageReference Include="Dapper" Version="2.*" />

  <!-- Optional -->
  <PackageReference Include="MessagePack" Version="2.*" />
  <PackageReference Include="Bogus" Version="35.*" />  <!-- Faker equivalent -->
</ItemGroup>
```
