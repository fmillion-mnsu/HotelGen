using System.ComponentModel;
using System.Runtime.InteropServices;

namespace Xl9045qi.HotelGen.Models
{
    /// <summary>
    /// Represents a charge attempt to settle a debt on a transaction.
    /// </summary>
    /// <remarks>
    /// The struct takes up exactly 64 bytes in memory.
    /// The padding is added to ensure that the struct size is a power of 2, 
    ///     which can improve performance when processing large arrays of transaction charges.
    /// </remarks>
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public unsafe struct TransactionCharge
    {
        /// <summary>
        /// The transaction ID associated with this charge. This should match the TransactionId in the corresponding Transaction record.
        /// </summary>
        public int TransactionId;
        /// <summary>
        /// UNIX timestamp (MSB) and 1/2^32nds of a second (LSB) of when the charge was attempted to the customer's account
        /// </summary>
        public long ChargeTimestamp; 
        /// <summary>
        /// The amount of the transaction, represented in thousandths of a cent (millicents)
        /// </summary>
        /// <remarks>One dollar = 100,000 millicents</remarks>
        public long AmountMillicents; // Amount in millcents (1/1000th of a cent) to avoid floating-point issues
        /// <summary>
        /// A string representing the payment method used.
        /// </summary>
        /// <example>"VISA x-1234"</example>
        /// <example>"Diners Club x-5678"</example>
        /// <example>"PayPal user@paypal.com"</example>        
        public fixed byte PaymentMethod[32]; 
        /// <summary>
        /// The result of the transaction attempt, represented as a byte value corresponding to the TransactionResult enum.
        /// </summary>
        public TransactionResult Result; 
        // 4 + 8 + 8 + 32 + 1 = 53 bytes
        // 64 - 53 = 11 bytes of padding

        private fixed byte _padding[11];
    }

    public static class TransactionChargeExtensions
    {
        public static unsafe string PaymentMethod(this ref TransactionCharge charge) => Helpers.GetUtf8String(charge.PaymentMethod, 32);
        public static unsafe void SetPaymentMethod(this ref TransactionCharge charge, string paymentMethod)
        {
            fixed (byte* paymentMethodPtr = charge.PaymentMethod)
            {
                Helpers.SetUtf8String(paymentMethodPtr, 32, paymentMethod);
            }
        }
    }
    /// <summary>
    /// Represents the result of a transaction charge attempt, such as whether it was successful or if there was an error (e.g., insufficient funds, card expired, etc.).
    /// </summary>
    public enum TransactionResult : byte
    {
        /// <summary>
        /// The payment was successfully charged.
        /// </summary>
        Success = 0,
        /// <summary>
        /// The payment was declined due to the account having insufficient funds.
        /// </summary>
        InsufficientFunds = 1,
        /// <summary>
        /// The payment was declined because the card used for the transaction has expired.
        /// </summary>
        CardExpired = 2,
        /// <summary>
        /// The payment was declined because the card number provided was invalid (e.g., failed Luhn check, incorrect length, etc.).
        /// </summary>
        InvalidCardNumber = 3,
        /// <summary>
        /// The payment was declined due to a network error while processing the payment.
        /// </summary>
        PaymentNetworkError = 4,
        /// <summary>
        /// The payment was declined because it was suspected to be fraudulent. The user may be asked to verify the transaction and retry.
        /// </summary>
        FraudSuspected = 5,
        /// <summary>
        /// The payment was declined due to an unspecified error.
        /// </summary>
        OtherError = 6
    }   
}
