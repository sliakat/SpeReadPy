/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* pil_platform.h - Teledyne Princeton Instruments Library Platform Support   */
/*                                                                            */
/*  Supported Platforms:                                                      */
/*      - PIL_WIN64                                                           */
/*      - PIL_WIN32                                                           */
/*      - PIL_LIN64                                                           */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
#if !defined PIL_PLATFORM_H
#define PIL_PLATFORM_H

/******************************************************************************/
/* OS Detection                                                               */
/******************************************************************************/
#if defined _WIN64
#    define PIL_WIN64
#elif defined _WIN32
#    define PIL_WIN32
#elif defined __linux__ && defined __x86_64__
#    define PIL_LIN64
#else
#   error PI Library - Platform Not Supported
#endif

/******************************************************************************/
/* Basic Native Data Types                                                    */
/******************************************************************************/
typedef          int    piint;  /* integer native to platform                 */
typedef          double piflt;  /* floating point native to platform          */
typedef          int    pibln;  /* boolean native to platform                 */
typedef          char   pichar; /* character native to platform               */
typedef unsigned char   pibyte; /* byte native to platform                    */
#if defined __cplusplus
    typedef      bool   pibool; /* C++ boolean native to platform             */
#endif

/******************************************************************************/
/* Basic Sized Data Types                                                     */
/******************************************************************************/
#if defined PIL_WIN64
    typedef signed   char      pi8s;  /* 8-bit signed integer                 */
    typedef unsigned char      pi8u;  /* 8-bit unsigned integer               */
    typedef          short     pi16s; /* 16-bit signed integer                */
    typedef unsigned short     pi16u; /* 16-bit unsigned integer              */
    typedef          long      pi32s; /* 32-bit signed integer                */
    typedef unsigned long      pi32u; /* 32-bit unsigned integer              */
    typedef          long long pi64s; /* 64-bit signed integer                */
    typedef unsigned long long pi64u; /* 64-bit unsigned integer              */
    typedef          float     pi32f; /* 32-bit floating point                */
    typedef          double    pi64f; /* 64-bit floating point                */
#elif defined PIL_WIN32
    typedef signed   char      pi8s;  /* 8-bit signed integer                 */
    typedef unsigned char      pi8u;  /* 8-bit unsigned integer               */
    typedef          short     pi16s; /* 16-bit signed integer                */
    typedef unsigned short     pi16u; /* 16-bit unsigned integer              */
    typedef          long      pi32s; /* 32-bit signed integer                */
    typedef unsigned long      pi32u; /* 32-bit unsigned integer              */
    typedef          long long pi64s; /* 64-bit signed integer                */
    typedef unsigned long long pi64u; /* 64-bit unsigned integer              */
    typedef          float     pi32f; /* 32-bit floating point                */
    typedef          double    pi64f; /* 64-bit floating point                */
#elif defined PIL_LIN64
    typedef signed   char      pi8s;  /* 8-bit signed integer                 */
    typedef unsigned char      pi8u;  /* 8-bit unsigned integer               */
    typedef          short     pi16s; /* 16-bit signed integer                */
    typedef unsigned short     pi16u; /* 16-bit unsigned integer              */
    typedef          int       pi32s; /* 32-bit signed integer                */
    typedef unsigned int       pi32u; /* 32-bit unsigned integer              */
    typedef          long      pi64s; /* 64-bit signed integer                */
    typedef unsigned long      pi64u; /* 64-bit unsigned integer              */
    typedef          float     pi32f; /* 32-bit floating point                */
    typedef          double    pi64f; /* 64-bit floating point                */
#else
#   error PI Library - Platform Missing Sized Data Type Definition
#endif

/******************************************************************************/
/* Function Declarations                                                      */
/******************************************************************************/
#if defined PIL_WIN64
#   define PIL_EXPORT_DEF extern "C"
#   define PIL_EXPORT     __declspec(dllexport)
#   define PIL_IMPORT     __declspec(dllimport)
#   define PIL_CALL       __stdcall
#elif defined PIL_WIN32
#   define PIL_EXPORT_DEF extern "C"
#   define PIL_EXPORT     __declspec(dllexport)
#   define PIL_IMPORT     __declspec(dllimport)
#   define PIL_CALL       __stdcall
#elif defined PIL_LIN64
#   define PIL_EXPORT_DEF extern "C" __attribute__((visibility("default")))
#   define PIL_EXPORT     __attribute__((visibility("default")))
#   define PIL_IMPORT     
#   define PIL_CALL       
#else
#   error PI Library - Platform Missing Function Declaration Definition
#endif

#endif
