using System.Runtime.InteropServices;

namespace Xl9045qi.HotelGen.Models
{
    /// <summary>
    /// Represents a customer of the hospitality network.
    /// </summary>
    /// <remarks>
    /// The struct takes up exactly 256 bytes in memory.
    /// The fixed-size UTF-8 strings allow for efficient storage and retrieval of customer information without the overhead of dynamic memory allocation.
    /// The padding is added to ensure that the struct size is a power of 2, 
    ///     which can improve performance when processing large arrays of customers.
    /// </remarks>
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public unsafe struct Customer
    {
        
        // UTF-8 strings (inline, fixed-size)
        /// <summary>
        /// First name of the customer.
        /// </summary>
        public fixed byte FirstNameUtf8[32];
        /// <summary>
        /// Last name of the customer.
        /// </summary>
        public fixed byte LastNameUtf8[32];
        /// <summary>
        /// Street address of the customer.
        /// </summary>
        public fixed byte StreetUtf8[64];
        /// <summary>
        /// City where the customer is located.
        /// </summary>
        public fixed byte CityUtf8[24];
        /// <summary>
        /// State where the customer is located.
        /// </summary>
        public fixed byte StateUtf8[2];
        /// <summary>
        /// ZIP code of the customer's location.
        /// </summary>
        public fixed byte ZipUtf8[10];
        /// <summary>
        /// Contact phone number for the customer.
        /// </summary>
        public fixed byte PhoneUtf8[16];
        /// <summary>
        /// Contact email address for the customer.
        /// </summary>
        public fixed byte EmailUtf8[64];
        // 32 + 32 + 64 + 24 + 2 + 10 + 16 + 64 = 244 bytes

        // 244 + 4 = 248 bytes
        // 256 - 248 = 8 padding bytes

        // Padding to reach power-of-2 size (e.g., 256 bytes)
        private fixed byte _padding[8];
    }

    public static class CustomerExtensions
    {
        public static unsafe string FirstName(this ref Customer customer) => Helpers.GetUtf8String(customer.FirstNameUtf8, 32);
        public static unsafe void SetFirstName(this ref Customer customer, string firstName)
        {
            fixed (byte* firstNamePtr = customer.FirstNameUtf8)
            {
                Helpers.SetUtf8String(firstNamePtr, 32, firstName);
            }
        }

        public static unsafe string LastName(this ref Customer customer) => Helpers.GetUtf8String(customer.LastNameUtf8, 32);
        public static unsafe void SetLastName(this ref Customer customer, string lastName)
        {
            fixed (byte* lastNamePtr = customer.LastNameUtf8)
            {
                Helpers.SetUtf8String(lastNamePtr, 32, lastName);
            }
        }

        public static unsafe string Street(this ref Customer customer) => Helpers.GetUtf8String(customer.StreetUtf8, 64);
        public static unsafe void SetStreet(this ref Customer customer, string street)
        {
            fixed (byte* streetPtr = customer.StreetUtf8)
            {
                Helpers.SetUtf8String(streetPtr, 64, street);
            }
        }

        public static unsafe string City(this ref Customer customer) => Helpers.GetUtf8String(customer.CityUtf8, 24);
        public static unsafe void SetCity(this ref Customer customer, string city)
        {
            fixed (byte* cityPtr = customer.CityUtf8)
            {
                Helpers.SetUtf8String(cityPtr, 24, city);
            }
        }

        public static unsafe string State(this ref Customer customer) => Helpers.GetUtf8String(customer.StateUtf8, 2);
        public static unsafe void SetState(this ref Customer customer, string state)
        {
            fixed (byte* statePtr = customer.StateUtf8)
            {
                Helpers.SetUtf8String(statePtr, 2, state);
            }
        }

        public static unsafe string Zip(this ref Customer customer) => Helpers.GetUtf8String(customer.ZipUtf8, 10);
        public static unsafe void SetZip(this ref Customer customer, string zip)
        {
            fixed (byte* zipPtr = customer.ZipUtf8)
            {
                Helpers.SetUtf8String(zipPtr, 10, zip);
            }
        }

        public static unsafe string Phone(this ref Customer customer) => Helpers.GetUtf8String(customer.PhoneUtf8, 16);
        public static unsafe void SetPhone(this ref Customer customer, string phone)
        {
            fixed (byte* phonePtr = customer.PhoneUtf8)
            {
                Helpers.SetUtf8String(phonePtr, 16, phone);
            }
        }

        public static unsafe string Email(this ref Customer customer) => Helpers.GetUtf8String(customer.EmailUtf8, 64);
        public static unsafe void SetEmail(this ref Customer customer, string email)
        {
            fixed (byte* emailPtr = customer.EmailUtf8)
            {
                Helpers.SetUtf8String(emailPtr, 64, email);
            }
        }
    }
}