using System.Runtime.InteropServices;

namespace Xl9045qi.HotelGen.Models
{
    /// <summary>
    /// Defines a property type within the hospitality network.
    /// </summary>
    public enum PropertyType : byte
    {
        /// <summary>
        /// Small, budget-friendly lodging option, often with limited amenities. (Example: roadside motel)
        /// </summary>
        Motel = 0,
        /// <summary>
        /// Larger lodging option with more amenities and services than a motel. (Example: city hotel)
        /// </summary>
        Hotel = 1,
        /// <summary>
        /// A destination offering extensive amenities, recreational facilities, and accommodations. (Example: beach resort)
        /// </summary>
        Resort = 2
    }

    /// <summary>
    /// Represents a property location within the hospitality network. (Example: hotel, resort)
    /// </summary>
    /// <remarks>
    /// The struct takes up exactly 512 bytes in memory.
    /// The padding is added to ensure that the struct size is a power of 2, 
    ///     which can improve performance when processing large arrays of properties.
    /// </remarks>
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public unsafe struct Property
    {
        /// <summary>
        /// Holds the type of hotel
        /// </summary>
        public PropertyType HotelType;
        // 4 bytes

        // UTF-8 strings (inline, fixed-size)
        /// <summary>
        /// Name of the hotel.
        /// </summary>
        public fixed byte NameUtf8[64];
        /// <summary>
        /// Street address of the hotel.
        /// </summary>
        public fixed byte StreetUtf8[64];
        /// <summary>
        /// City where the hotel is located.
        /// </summary>
        public fixed byte CityUtf8[24];
        /// <summary>
        /// State where the hotel is located.
        /// </summary>
        public fixed byte StateUtf8[2];
        /// <summary>
        /// ZIP code of the hotel's location.
        /// </summary>
        public fixed byte ZipUtf8[10];
        /// <summary>
        /// Contact phone number for the hotel.
        /// </summary>
        public fixed byte PhoneUtf8[16];
        /// <summary>
        /// Contact email address for the hotel.
        /// </summary>
        public fixed byte EmailUtf8[64];
        /// <summary>
        /// Website URL of the hotel.
        /// </summary>
        public fixed byte WebsiteUtf8[64];
        // 64 + 64 + 24 + 2 + 10 + 16 + 64 + 64 = 308 bytes

        // 308 + 4 = 312 bytes
        // 512 - 312 = 200 padding bytes

        // Padding to reach power-of-2 size (e.g., 256 bytes)
        private fixed byte _padding[200];
    }

    public static class PropertyExtensions
    {
        public static unsafe string Name(this ref Property property) => Helpers.GetUtf8String(property.NameUtf8, 64);
        public static unsafe void SetName(this ref Property property, string name)
        {
            fixed (byte* namePtr = property.NameUtf8)
            {
                Helpers.SetUtf8String(namePtr, 64, name);
            }
        }
        public static unsafe string Street(this ref Property property) => Helpers.GetUtf8String(property.StreetUtf8, 64);
        public static unsafe void SetStreet(this ref Property property, string street) 
        {
            fixed (byte* streetPtr = property.StreetUtf8)
            {
                Helpers.SetUtf8String(streetPtr, 64, street);
            }
        }
        public static unsafe string City(this ref Property property) => Helpers.GetUtf8String(property.CityUtf8, 24);
        public static unsafe void SetCity(this ref Property property, string city)
        {
            fixed (byte* cityPtr = property.CityUtf8)
            {
                Helpers.SetUtf8String(cityPtr, 24, city);
            }
        }

        public static unsafe string State(this ref Property property) => Helpers.GetUtf8String(property.StateUtf8, 2);
        public static unsafe void SetState(this ref Property property, string state)
        {
            fixed (byte* statePtr = property.StateUtf8)
            {
                Helpers.SetUtf8String(statePtr, 2, state);
            }
        }

        public static unsafe string Zip(this ref Property property) => Helpers.GetUtf8String(property.ZipUtf8, 10);
        public static unsafe void SetZip(this ref Property property, string zip) 
        {
            fixed (byte* zipPtr = property.ZipUtf8)
            {
                Helpers.SetUtf8String(zipPtr, 10, zip);
            }   
        }

        public static unsafe string Phone(this ref Property property) => Helpers.GetUtf8String(property.PhoneUtf8, 16);
        public static unsafe void SetPhone(this ref Property property, string phone)
        {
            fixed (byte* phonePtr = property.PhoneUtf8)
            {
                Helpers.SetUtf8String(phonePtr, 16, phone);
            }
        }

        public static unsafe string Email(this ref Property property) => Helpers.GetUtf8String(property.EmailUtf8, 64);
        public static unsafe void SetEmail(this ref Property property, string email)
        {
            fixed (byte* emailPtr = property.EmailUtf8)
            {
                Helpers.SetUtf8String(emailPtr, 64, email);
            }
        }

        public static unsafe string Website(this ref Property property) => Helpers.GetUtf8String(property.WebsiteUtf8, 64);
        public static unsafe void SetWebsite(this ref Property property, string website)
        {
            fixed (byte* websitePtr = property.WebsiteUtf8)
            {
                Helpers.SetUtf8String(websitePtr, 64, website);                    
            }
        }
    }
}