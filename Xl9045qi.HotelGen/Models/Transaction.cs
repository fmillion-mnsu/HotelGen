using System.Runtime.InteropServices;

namespace Xl9045qi.HotelGen.Models
{
    /// <summary>
    /// Represents a transaction.
    /// </summary>
    /// <remarks>
    /// The struct takes up exactly 32 bytes in memory.
    /// The padding is added to ensure that the struct size is a power of 2, 
    ///     which can improve performance when processing large arrays of transactions.
    /// </remarks>
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public unsafe struct Transaction
    {
        /// <summary>
        /// The customer ID this transaction refers to.
        /// </summary>
        public int CustomerId;
        /// <summary>
        /// The property ID this transaction refers to.
        /// </summary>
        public int PropertyId;
        /// <summary>
        /// UNIX timestamp (MSB) and 1/2^32nds of a second (LSB) of when the transaction occurred
        /// </summary>
        public long TransactionTimestamp; 
        /// <summary>
        /// The total for this transaction, in millicents (1/1000th of a cent) to avoid floating-point issues.
        /// </summary>
        public long AmountMillicents;
        // 4 + 4 + 8 + 8 = 24 bytes
        // 32 - 24 = 8 padding bytes

        // Padding to reach power-of-2 size (32 bytes)
        private fixed byte _padding[8];
    }

}