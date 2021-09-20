using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Runtime.InteropServices;

namespace SL_PicamSample
{
    class Picam
    {
        [StructLayout(LayoutKind.Sequential, Size = 64)]
        public struct TempSensor
        {
        }
        [StructLayout(LayoutKind.Sequential, Size = 64)]
        public struct TempSerial
        {
        }

        public struct PicamCameraID
        {
            public int model;
            public int computer_interface;
            public TempSensor sensor_name;
            public TempSerial serial_number;

            public string GetSensor()
            {
                IntPtr ptr = IntPtr.Zero;
                try
                {
                    ptr = Marshal.AllocHGlobal(64);
                    Marshal.StructureToPtr(sensor_name, ptr, false);
                    return Marshal.PtrToStringAnsi(ptr);
                }
                finally
                {
                    if (ptr != IntPtr.Zero)
                    {
                        Marshal.FreeHGlobal(ptr);
                    }
                }
            }
        }

        public struct PicamAvailableData
        {
            public IntPtr initial_readout;
            public long readout_count;
        }

        public struct PicamAcquisitionStatus
        {
            public bool running;
            public int errors;
            public double readout_rate;
        }

        public struct PicamAcquisitionBuffer
        {
            public IntPtr memory;
            public long memory_size;
        }



        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_InitializeLibrary();
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_UninitializeLibrary();
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_OpenFirstCamera(ref IntPtr camera);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_ConnectDemoCamera(int model, char[] serial_number, ref PicamCameraID id);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_OpenCamera(ref PicamCameraID id, ref IntPtr camera);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_GetCameraID(IntPtr camera, ref PicamCameraID id);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int PicamAdvanced_GetCameraDevice(IntPtr camera, ref IntPtr device);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_StartAcquisition(IntPtr camera);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_WaitForAcquisitionUpdate(IntPtr camera, int readout_time_out, ref PicamAvailableData available, ref PicamAcquisitionStatus status);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_SetParameterLargeIntegerValue(IntPtr camera, int parameter, int value);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_CommitParameters(IntPtr camera, ref int[] failed_parameter_array, ref int failed_parameter_count);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_GetParameterFloatingPointValue(IntPtr camera, int parameter, ref double value);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_GetParameterIntegerValue(IntPtr camera, int parameter, ref int value);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int PicamAdvanced_SetAcquisitionBuffer(IntPtr device, ref PicamAcquisitionBuffer buffer);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int PicamAdvanced_GetAcquisitionBuffer(IntPtr device, ref PicamAcquisitionBuffer buffer);
        [DllImport("C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern int Picam_CloseCamera(IntPtr camera);

        public static int ParameterValue(int v, int c, int n)
        {
            return ((c << 24) + (v << 16) + n);
        }

        public static void Acquire(IntPtr device, int frames)
        {
            int error;
            int failedCount = 0;            
            int[] failedArray = new int[2]; //increase size if error thrown for too little size
            int readStride = 0;
            int offset = 0;
            PicamAvailableData available = new PicamAvailableData();
            PicamAcquisitionStatus status = new PicamAcquisitionStatus();
            PicamAcquisitionBuffer buffer = new PicamAcquisitionBuffer();
            PicamAcquisitionBuffer createdBuffer = new PicamAcquisitionBuffer();
            error = Picam_SetParameterLargeIntegerValue(device, ParameterValue(6, 2, 40), frames);
            //Console.Write("Set Parameter Error: " + error.ToString());
            error = Picam_CommitParameters(device, ref failedArray, ref failedCount);
            //Console.WriteLine(" Commit Error: " + error.ToString() + " Failed Count: " + failedCount.ToString());
            Picam_GetParameterIntegerValue(device, ParameterValue(1, 1, 45), ref readStride);
            byte[] frame = new byte[readStride];
            IntPtr circBuff = Marshal.AllocHGlobal(readStride * 3);
            UInt16[] frameVal = new UInt16[readStride / 2];
            buffer.memory = circBuff;
            buffer.memory_size = readStride * 3;


            error = PicamAdvanced_SetAcquisitionBuffer(device, ref buffer);
            error = PicamAdvanced_GetAcquisitionBuffer(device, ref createdBuffer);
            Console.WriteLine("Circular Buffer manually set to: " + createdBuffer.memory_size.ToString() + " bytes.\n");

            Picam_StartAcquisition(device);
            Console.WriteLine("Acquiring...");
            do
            {
                error = Picam_WaitForAcquisitionUpdate(device, 1000, ref available, ref status);
                if (available.readout_count > 0)
                {
                    offset = ((int)available.readout_count - 1) * readStride;
                    Marshal.Copy(available.initial_readout, frame, offset, readStride);
                    Buffer.BlockCopy(frame, 0, frameVal, 0, readStride);
                    Console.WriteLine("\tFrame(s) Captured. Readout Count: " + available.readout_count.ToString() + 
                        ". Readout Rate: " + status.readout_rate.ToString("N2") + "fps. Center Pixel Value: " + frameVal[(frameVal.Length)/2].ToString());
                }
                
            } while (status.running || error == 32);
            Console.WriteLine("...Acquisition Finished!");
            Marshal.FreeHGlobal(circBuff);
        }
        
    }

    class Program
    {
        static void Main(string[] args)
        {
            int err;
            Picam.PicamCameraID id = new Picam.PicamCameraID();
            IntPtr cam = new IntPtr(0);
            IntPtr dev = new IntPtr(0);
            err = Picam.Picam_InitializeLibrary();
            err = Picam.Picam_OpenFirstCamera(ref cam);
            if (err != 0)
            {
                err = Picam.Picam_ConnectDemoCamera(55, "01234567".ToCharArray(), ref id);
                err = Picam.Picam_OpenCamera(ref id, ref cam);
                Console.WriteLine("No Live Camera Found, ***Opened Demo Camera.***");
            }
            else
            {
                err = Picam.Picam_GetCameraID(cam, ref id);
                Console.WriteLine("Live Camera Opened.");
            }
            Console.WriteLine("Sensor Opened : " + id.GetSensor());
            //Console.WriteLine("Open Error: " + err.ToString());
            err = Picam.PicamAdvanced_GetCameraDevice(cam, ref dev);
            Picam.Acquire(dev, 20);
            err = Picam.Picam_CloseCamera(dev);
            err = Picam.Picam_UninitializeLibrary();
        }
    }
}
