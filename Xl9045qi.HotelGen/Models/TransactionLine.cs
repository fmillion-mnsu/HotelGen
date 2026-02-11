using System.ComponentModel;
using System.Runtime.InteropServices;

namespace Xl9045qi.HotelGen.Models
{
    /// <summary>
    /// Represents a line item on a transaction, such as a specific charge or fee. Each transaction can have multiple lines, which together make up the total amount of the transaction.
    /// </summary>
    /// <remarks>
    /// The struct takes up exactly 128 bytes in memory.
    /// The padding is added to ensure that the struct size is a power of 2, 
    ///     which can improve performance when processing large arrays of transaction lines.
    /// </remarks>
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public unsafe struct TransactionLine
    {
        /// <summary>
        /// Line number (order) of this line on the transaction.
        /// </summary>
        public short LineNumber; 
        /// <summary>
        /// The transaction ID associated with this line item. This should match the TransactionId in the corresponding Transaction record.
        /// </summary>
        public int TransactionId;
        /// <summary>
        /// Description of the line item on the transaction.
        /// </summary>
        public fixed byte Description[64]; // Description of the charge (e.g., "Room charge for 2024-01-01")
        /// <summary>
        /// The amount of this line item, represented in thousandths of a cent (millicents)
        /// </summary>
        /// <remarks>One dollar = 100,000 millicents</remarks>
        public long AmountMillicents; // Amount in millcents (1/1000th of a cent) to avoid floating-point issues

        // 2 + 4 + 64 + 8 = 78 bytes
        // 128 - 78 = 50 bytes of padding
        
        private fixed byte _padding[50];
    }

    public static class TransactionLineExtensions
    {
        public static unsafe string Description(this ref TransactionLine line) => Helpers.GetUtf8String(line.Description, 64);
        public static unsafe void SetDescription(this ref TransactionLine line, string description) 
        {
            fixed (byte* descriptionPtr = line.Description)
            {
                Helpers.SetUtf8String(descriptionPtr, 64, description);
            }
        }
        }
}
