/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* picam_accessory.h - Teledyne Princeton Instruments Accessory Control API   */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
#if !defined PICAM_ACCESSORY_H
#define PICAM_ACCESSORY_H

#include "picam_advanced.h"

/******************************************************************************/
/* C++ Prologue                                                               */
/******************************************************************************/
#if defined __cplusplus && !defined PICAM_EXPORTS
    extern "C"
    {
#endif

/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* Accessory Identification, Plug 'n Play Discovery, Access and Information   */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/

/*----------------------------------------------------------------------------*/
/* Accessory Identification --------------------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamAccessoryID
{
    PicamModel             model;
    PicamComputerInterface computer_interface;
    pichar                 serial_number[PicamStringSize_SerialNumber];
} PicamAccessoryID;
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_DestroyAccessoryIDs(
    const PicamAccessoryID* id_array );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetAvailableAccessoryIDs(
    const PicamAccessoryID** id_array,
    piint*                   id_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetUnavailableAccessoryIDs(
    const PicamAccessoryID** id_array,
    piint*                   id_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_IsAccessoryIDConnected(
    const PicamAccessoryID* id,
    pibln*                  connected );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_IsAccessoryIDOpenElsewhere(
    const PicamAccessoryID* id,
    pibln*                  open_elsewhere );
/*----------------------------------------------------------------------------*/
/* Accessory Plug 'n Play Discovery ------------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamAccessoryDiscoveryCallback)(
    const PicamAccessoryID* id,
    PicamHandle             accessory,
    PicamDiscoveryAction    action );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_RegisterForDiscovery(
    PicamAccessoryDiscoveryCallback discover ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_UnregisterForDiscovery(
    PicamAccessoryDiscoveryCallback discover ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_DiscoverAccessories( void );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_StopDiscoveringAccessories( void );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_IsDiscoveringAccessories( pibln* discovering );
/*----------------------------------------------------------------------------*/
/* Accessory Access ----------------------------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_OpenFirstAccessory( PicamHandle* accessory );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_OpenAccessory(
    const PicamAccessoryID* id,
    PicamHandle*            accessory );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_CloseAccessory( PicamHandle accessory );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetOpenAccessories(
    const PicamHandle** accessory_array,
    piint*              accessory_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_IsAccessoryConnected(
    PicamHandle accessory,
    pibln*      connected );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetAccessoryID(
    PicamHandle       accessory,
    PicamAccessoryID* id );
/*----------------------------------------------------------------------------*/
/* Accessory Information - Calibration ---------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetLightSourceReference(
    PicamHandle              accessory,
    const PicamCalibration** counts_vs_nm ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
/* Accessory Information - Firmware ------------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAccessory_GetFirmwareDetails(
    const PicamAccessoryID*     id,
    const PicamFirmwareDetail** firmware_array,
    piint*                      firmware_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
/* Accessory Information - User State ----------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_GetUserState                                            */
/*      PicamAdvanced_SetUserState                                            */
/*----------------------------------------------------------------------------*/

/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* Accessory Parameter Values, Information and Constraints                    */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/

/*----------------------------------------------------------------------------*/
/* Accessory Parameters ------------------------------------------------------*/
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Integer --------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterIntegerValue                                        */
/*      Picam_SetParameterIntegerValue                                        */
/*      Picam_CanSetParameterIntegerValue                                     */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_RegisterForIntegerValueChanged                          */
/*      PicamAdvanced_UnregisterForIntegerValueChanged                        */
/*      PicamAdvanced_RegisterForExtrinsicIntegerValueChanged                 */
/*      PicamAdvanced_UnregisterForExtrinsicIntegerValueChanged               */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Floating Point -------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterFloatingPointValue                                  */
/*      Picam_SetParameterFloatingPointValue                                  */
/*      Picam_CanSetParameterFloatingPointValue                               */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_RegisterForFloatingPointValueChanged                    */
/*      PicamAdvanced_UnregisterForFloatingPointValueChanged                  */
/*      PicamAdvanced_RegisterForExtrinsicFloatingPointValueChanged           */
/*      PicamAdvanced_UnregisterForExtrinsicFloatingPointValueChanged         */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Default --------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterIntegerDefaultValue                                 */
/*      Picam_GetParameterFloatingPointDefaultValue                           */
/*      Picam_RestoreParametersToDefaultValues                                */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Online ---------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_CanSetParameterOnline ^                                         */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Reading --------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_CanReadParameter ^                                              */
/*      Picam_ReadParameterIntegerValue ^                                     */
/*      Picam_ReadParameterFloatingPointValue ^                               */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Values - Status Waiting -------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_CanWaitForStatusParameter                                       */
/*      Picam_GetStatusParameterPurview                                       */
/*      Picam_EstimateTimeToStatusParameterValue                              */
/*      Picam_WaitForStatusParameterValue                                     */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_NotifyWhenStatusParameterValue                          */
/*      PicamAdvanced_CancelNotifyWhenStatusParameterValue                    */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Information - Available Parameters --------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameters                                                   */
/*      Picam_DoesParameterExist                                              */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Information - Relevance -------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_IsParameterRelevant                                             */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_RegisterForIsRelevantChanged                            */
/*      PicamAdvanced_UnregisterForIsRelevantChanged                          */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Information - Value Type ------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterValueType                                           */
/*      Picam_GetParameterEnumeratedType                                      */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Information - Value Access ----------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterValueAccess                                         */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_RegisterForValueAccessChanged ^                         */
/*      PicamAdvanced_UnregisterForValueAccessChanged ^                       */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Information - Dynamics --------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_GetParameterDynamics                                    */
/*      PicamAdvanced_GetParameterExtrinsicDynamics                           */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Constraints - Constraint Type -------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterConstraintType                                      */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Constraints - Collection ------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterCollectionConstraint                                */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_GetParameterCollectionConstraints                       */
/*      PicamAdvanced_RegisterForDependentCollectionConstraintChanged ^       */
/*      PicamAdvanced_UnregisterForDependentCollectionConstraintChanged ^     */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Constraints - Range -----------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_GetParameterRangeConstraint                                     */
/*  picam_advanced.h:                                                         */
/*      PicamAdvanced_GetParameterRangeConstraints                            */
/*      PicamAdvanced_RegisterForDependentRangeConstraintChanged ^            */
/*      PicamAdvanced_UnregisterForDependentRangeConstraintChanged ^          */
/*----------------------------------------------------------------------------*/
/* Accessory Parameter Commitment --------------------------------------------*/
/*----------------------------------------------------------------------------*/
/*  picam.h:                                                                  */
/*      Picam_AreParametersCommitted ^                                        */
/*      Picam_CommitParameters ^                                              */
/*----------------------------------------------------------------------------*/
/* ^ supported for completeness but provides no or redundant functionality    */
/*----------------------------------------------------------------------------*/

/******************************************************************************/
/* C++ Epilogue                                                               */
/******************************************************************************/
#if defined __cplusplus && !defined PICAM_EXPORTS
    }   /* end extern "C" */
#endif

#endif
