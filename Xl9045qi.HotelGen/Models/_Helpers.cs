using System.Text;

namespace Xl9045qi.HotelGen.Models
{
    public static unsafe class Helpers
    {
        public static void SetUtf8String(byte* dest, int maxLength, string source)
        {
            if (string.IsNullOrEmpty(source))
            {
                dest[0] = 0;
                return;
            }
            
            var destSpan = new Span<byte>(dest, maxLength);
            int bytesWritten = Encoding.UTF8.GetBytes(source.AsSpan(), 
                                                    destSpan.Slice(0, maxLength - 1));
            destSpan[bytesWritten] = 0;  // Null terminate
            
            
            if (bytesWritten + 1 < maxLength)
                destSpan.Slice(bytesWritten + 1).Clear();
        }
        
        public static string GetUtf8String(byte* source, int maxLength)
        {
            int length = 0;
            while (length < maxLength && source[length] != 0)
                length++;
            
            return length == 0 ? string.Empty : Encoding.UTF8.GetString(source, length);
        }
    }    
}
