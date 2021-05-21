/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* picam_advanced.h - Teledyne Princeton Instruments Advanced Control API     */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
#if !defined PICAM_ADVANCED_H
#define PICAM_ADVANCED_H

#include "picam.h"

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
/* Camera Plug 'n Play Discovery, Access and Information                      */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/

/*----------------------------------------------------------------------------*/
/* Camera/Accessory Plug 'n Play Discovery -----------------------------------*/
/*----------------------------------------------------------------------------*/
typedef enum PicamDiscoveryAction
{
    PicamDiscoveryAction_Found   = 1,
    PicamDiscoveryAction_Lost    = 2,
    PicamDiscoveryAction_Faulted = 3
} PicamDiscoveryAction; /* (4) */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamDiscoveryCallback)(
    const PicamCameraID* id,
    PicamHandle          device,
    PicamDiscoveryAction action );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDiscovery(
    PicamDiscoveryCallback discover ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDiscovery(
    PicamDiscoveryCallback discover ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_DiscoverCameras( void );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_StopDiscoveringCameras( void );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_IsDiscoveringCameras( pibln* discovering );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Access ---------------------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef enum PicamHandleType
{
    PicamHandleType_CameraDevice  = 1,
    PicamHandleType_CameraModel   = 2,
    PicamHandleType_Accessory     = 4,
    PicamHandleType_EMCalibration = 3
} PicamHandleType; /* (5) */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetHandleType(
    PicamHandle      handle,
    PicamHandleType* type );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_OpenCameraDevice(
    const PicamCameraID* id,
    PicamHandle*         device );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_CloseCameraDevice( PicamHandle device );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetOpenCameraDevices(
    const PicamHandle** device_array,
    piint*              device_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetCameraModel(
    PicamHandle  camera,
    PicamHandle* model );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetCameraDevice(
    PicamHandle  camera,
    PicamHandle* device );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Information - User State ---------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetUserState(
    PicamHandle camera_or_accessory,
    void**      user_state );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_SetUserState(
    PicamHandle camera_or_accessory,
    void*       user_state );
/*----------------------------------------------------------------------------*/
/* Camera Information - Pixel Defects ----------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamPixelLocation
{
    pi16s x;
    pi16s y;
} PicamPixelLocation;
/*----------------------------------------------------------------------------*/
typedef struct PicamColumnDefect
{
    PicamPixelLocation start;
    piint              height;
} PicamColumnDefect;
/*----------------------------------------------------------------------------*/
typedef struct PicamRowDefect
{
    PicamPixelLocation start;
    piint              width;
} PicamRowDefect;
/*----------------------------------------------------------------------------*/
typedef struct PicamPixelDefectMap
{
    const PicamColumnDefect*  column_defect_array;
    piint                     column_defect_count;
    const PicamRowDefect*     row_defect_array;
    piint                     row_defect_count;
    const PicamPixelLocation* point_defect_array;
    piint                     point_defect_count;
} PicamPixelDefectMap;
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_DestroyPixelDefectMaps(
    const PicamPixelDefectMap* pixel_defect_map_array );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetPixelDefectMap(
    PicamHandle                 camera,
    const PicamPixelDefectMap** pixel_defect_map ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
/* Camera Information - Star Defects -----------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamStarDefect
{
    PicamPixelLocation center;
    pi32f              bias;
    pi32f              adjacent_factor;
    pi32f              diagonal_factor;
} PicamStarDefect;
/*----------------------------------------------------------------------------*/
typedef struct PicamStarDefectMap
{
    piint                  id;
    const PicamStarDefect* star_defect_array;
    piint                  star_defect_count;
} PicamStarDefectMap;
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_DestroyStarDefectMaps(
    const PicamStarDefectMap* star_defect_map_array );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetStarDefectMap(
    PicamHandle                camera,
    const PicamStarDefectMap** star_defect_map ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetStarDefectMaps(
    PicamHandle                camera,
    const PicamStarDefectMap** star_defect_map_array,
    piint*                     star_defect_map_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/

/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* Camera/Accessory Parameter Values, Information, Constraints and Commitment */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/

/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameters -----------------------------------------------*/
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Values - Integer -------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamIntegerValueChangedCallback)(
    PicamHandle    camera_or_accessory,
    PicamParameter parameter,
    piint          value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForIntegerValueChanged(
    PicamHandle                      camera_or_accessory,
    PicamParameter                   parameter,
    PicamIntegerValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForIntegerValueChanged(
    PicamHandle                      camera_or_accessory,
    PicamParameter                   parameter,
    PicamIntegerValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForExtrinsicIntegerValueChanged(
    PicamHandle                      device_or_accessory,
    PicamParameter                   parameter,
    PicamIntegerValueChangedCallback changed ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForExtrinsicIntegerValueChanged(
    PicamHandle                      device_or_accessory,
    PicamParameter                   parameter,
    PicamIntegerValueChangedCallback changed ); /* ASYNC */
/*----------------------------------------------------------------------------*/
/* Camera Parameter Values - Large Integer -----------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamLargeIntegerValueChangedCallback)(
    PicamHandle    camera,
    PicamParameter parameter,
    pi64s          value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForLargeIntegerValueChanged(
    PicamHandle                           camera,
    PicamParameter                        parameter,
    PicamLargeIntegerValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForLargeIntegerValueChanged(
    PicamHandle                           camera,
    PicamParameter                        parameter,
    PicamLargeIntegerValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Values - Floating Point ------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamFloatingPointValueChangedCallback)(
    PicamHandle    camera_or_accessory,
    PicamParameter parameter,
    piflt          value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForFloatingPointValueChanged(
    PicamHandle                            camera_or_accessory,
    PicamParameter                         parameter,
    PicamFloatingPointValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForFloatingPointValueChanged(
    PicamHandle                            camera_or_accessory,
    PicamParameter                         parameter,
    PicamFloatingPointValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForExtrinsicFloatingPointValueChanged(
    PicamHandle                            device_or_accessory,
    PicamParameter                         parameter,
    PicamFloatingPointValueChangedCallback changed ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForExtrinsicFloatingPointValueChanged(
    PicamHandle                            device_or_accessory,
    PicamParameter                         parameter,
    PicamFloatingPointValueChangedCallback changed ); /* ASYNC */
/*----------------------------------------------------------------------------*/
/* Camera Parameter Values - Regions of Interest -----------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamRoisValueChangedCallback)(
    PicamHandle      camera,
    PicamParameter   parameter,
    const PicamRois* value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForRoisValueChanged(
    PicamHandle                   camera,
    PicamParameter                parameter,
    PicamRoisValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForRoisValueChanged(
    PicamHandle                   camera,
    PicamParameter                parameter,
    PicamRoisValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Parameter Values - Pulse -------------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamPulseValueChangedCallback)(
    PicamHandle       camera,
    PicamParameter    parameter,
    const PicamPulse* value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForPulseValueChanged(
    PicamHandle                    camera,
    PicamParameter                 parameter,
    PicamPulseValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForPulseValueChanged(
    PicamHandle                    camera,
    PicamParameter                 parameter,
    PicamPulseValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Parameter Values - Custom Intensifier Modulation Sequence ----------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamModulationsValueChangedCallback)(
    PicamHandle             camera,
    PicamParameter          parameter,
    const PicamModulations* value );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForModulationsValueChanged(
    PicamHandle                          camera,
    PicamParameter                       parameter,
    PicamModulationsValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForModulationsValueChanged(
    PicamHandle                          camera,
    PicamParameter                       parameter,
    PicamModulationsValueChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Values - Status Waiting ------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamWhenStatusParameterValueCallback)(
    PicamHandle    device_or_accessory,
    PicamParameter parameter,
    piint          value,
    PicamError     error );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_NotifyWhenStatusParameterValue(
    PicamHandle                           device_or_accessory,
    PicamParameter                        parameter,
    piint                                 value,
    PicamWhenStatusParameterValueCallback when ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_CancelNotifyWhenStatusParameterValue(
    PicamHandle                           device_or_accessory,
    PicamParameter                        parameter,
    piint                                 value,
    PicamWhenStatusParameterValueCallback when ); /* ASYNC */
/*----------------------------------------------------------------------------*/
/* Camera Parameter Information - Relevance ----------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamIsRelevantChangedCallback)(
    PicamHandle    camera_or_accessory,
    PicamParameter parameter,
    pibln          relevant );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForIsRelevantChanged(
    PicamHandle                    camera_or_accessory,
    PicamParameter                 parameter,
    PicamIsRelevantChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForIsRelevantChanged(
    PicamHandle                    camera_or_accessory,
    PicamParameter                 parameter,
    PicamIsRelevantChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Information - Value Access ---------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamValueAccessChangedCallback)(
    PicamHandle      camera_or_accessory,
    PicamParameter   parameter,
    PicamValueAccess access );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForValueAccessChanged(
    PicamHandle                     camera_or_accessory,
    PicamParameter                  parameter,
    PicamValueAccessChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForValueAccessChanged(
    PicamHandle                     camera_or_accessory,
    PicamParameter                  parameter,
    PicamValueAccessChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Information - Dynamics -------------------------*/
/*----------------------------------------------------------------------------*/
typedef enum PicamDynamicsMask
{
    PicamDynamicsMask_None        = 0x0,
    PicamDynamicsMask_Value       = 0x1,
    PicamDynamicsMask_ValueAccess = 0x2,
    PicamDynamicsMask_IsRelevant  = 0x4,
    PicamDynamicsMask_Constraint  = 0x8
} PicamDynamicsMask; /* (0x10) */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterDynamics(
    PicamHandle        camera_or_accessory,
    PicamParameter     parameter,
    PicamDynamicsMask* dynamics );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterExtrinsicDynamics(
    PicamHandle        camera_or_accessory,
    PicamParameter     parameter,
    PicamDynamicsMask* extrinsic );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Constraints - Collection -----------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterCollectionConstraints(
    PicamHandle                       camera_or_accessory,
    PicamParameter                    parameter,
    const PicamCollectionConstraint** constraint_array,
    piint*                            constraint_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL*PicamDependentCollectionConstraintChangedCallback)(
    PicamHandle                      camera_or_accessory,
    PicamParameter                   parameter,
    const PicamCollectionConstraint* constraint );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDependentCollectionConstraintChanged(
    PicamHandle                                       camera_or_accessory,
    PicamParameter                                    parameter,
    PicamDependentCollectionConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDependentCollectionConstraintChanged(
    PicamHandle                                       camera_or_accessory,
    PicamParameter                                    parameter,
    PicamDependentCollectionConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera/Accessory Parameter Constraints - Range ----------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterRangeConstraints(
    PicamHandle                  camera_or_accessory,
    PicamParameter               parameter,
    const PicamRangeConstraint** constraint_array,
    piint*                       constraint_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL*PicamDependentRangeConstraintChangedCallback)(
    PicamHandle                 camera_or_accessory,
    PicamParameter              parameter,
    const PicamRangeConstraint* constraint );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDependentRangeConstraintChanged(
    PicamHandle                                  camera_or_accessory,
    PicamParameter                               parameter,
    PicamDependentRangeConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDependentRangeConstraintChanged(
    PicamHandle                                  camera_or_accessory,
    PicamParameter                               parameter,
    PicamDependentRangeConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Parameter Constraints - Regions of Interest ------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterRoisConstraints(
    PicamHandle                 camera,
    PicamParameter              parameter,
    const PicamRoisConstraint** constraint_array,
    piint*                      constraint_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamDependentRoisConstraintChangedCallback)(
    PicamHandle                camera,
    PicamParameter             parameter,
    const PicamRoisConstraint* constraint );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDependentRoisConstraintChanged(
    PicamHandle                                 camera,
    PicamParameter                              parameter,
    PicamDependentRoisConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDependentRoisConstraintChanged(
    PicamHandle                                 camera,
    PicamParameter                              parameter,
    PicamDependentRoisConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Parameter Constraints - Pulse --------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterPulseConstraints(
    PicamHandle                  camera,
    PicamParameter               parameter,
    const PicamPulseConstraint** constraint_array,
    piint*                       constraint_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamDependentPulseConstraintChangedCallback)(
    PicamHandle                 camera,
    PicamParameter              parameter,
    const PicamPulseConstraint* constraint );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDependentPulseConstraintChanged(
    PicamHandle                                  camera,
    PicamParameter                               parameter,
    PicamDependentPulseConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDependentPulseConstraintChanged(
    PicamHandle                                  camera,
    PicamParameter                               parameter,
    PicamDependentPulseConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Parameter Constraints - Custom Intensifier Modulation Sequence -----*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetParameterModulationsConstraints(
    PicamHandle                        camera,
    PicamParameter                     parameter,
    const PicamModulationsConstraint** constraint_array,
    piint*                             constraint_count ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamDependentModulationsConstraintChangedCallback)(
    PicamHandle                       camera,
    PicamParameter                    parameter,
    const PicamModulationsConstraint* constraint );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForDependentModulationsConstraintChanged(
    PicamHandle                                        camera,
    PicamParameter                                     parameter,
    PicamDependentModulationsConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForDependentModulationsConstraintChanged(
    PicamHandle                                        camera,
    PicamParameter                                     parameter,
    PicamDependentModulationsConstraintChangedCallback changed );
/*----------------------------------------------------------------------------*/
/* Camera Commitment ---------------------------------------------------------*/
/*----------------------------------------------------------------------------*/
/* Camera Parameter Validation -----------------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamValidationResult
{
    pibln                       is_valid;
    const PicamParameter*       failed_parameter;
    const PicamConstraintScope* failed_error_constraint_scope;
    const PicamConstraintScope* failed_warning_constraint_scope;
    const PicamParameter*       error_constraining_parameter_array;
    piint                       error_constraining_parameter_count;
    const PicamParameter*       warning_constraining_parameter_array;
    piint                       warning_constraining_parameter_count;
} PicamValidationResult;
/*----------------------------------------------------------------------------*/
PICAM_API Picam_DestroyValidationResult(
    const PicamValidationResult* result );
/*----------------------------------------------------------------------------*/
typedef struct PicamValidationResults
{
    pibln                        is_valid;
    const PicamValidationResult* validation_result_array;
    piint                        validation_result_count;
} PicamValidationResults;
/*----------------------------------------------------------------------------*/
PICAM_API Picam_DestroyValidationResults(
    const PicamValidationResults* results );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_ValidateParameter(
    PicamHandle                   model,
    PicamParameter                parameter,
    const PicamValidationResult** result ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_ValidateParameters(
    PicamHandle                    model,
    const PicamValidationResults** results ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
/* Camera Dependent Parameter Validation -------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamFailedDependentParameter
{
    PicamParameter              failed_parameter;
    const PicamConstraintScope* failed_error_constraint_scope;
    const PicamConstraintScope* failed_warning_constraint_scope;
} PicamFailedDependentParameter;
/*----------------------------------------------------------------------------*/
typedef struct PicamDependentValidationResult
{
    pibln                                is_valid;
    PicamParameter                       constraining_parameter;
    const PicamFailedDependentParameter* failed_dependent_parameter_array;
    piint                                failed_dependent_parameter_count;
} PicamDependentValidationResult;
/*----------------------------------------------------------------------------*/
PICAM_API Picam_DestroyDependentValidationResult(
    const PicamDependentValidationResult* result );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_ValidateDependentParameter(
    PicamHandle                            model,
    PicamParameter                         parameter,
    const PicamDependentValidationResult** result ); /* ALLOCATES */
/*----------------------------------------------------------------------------*/
/* Camera Parameter Commitment -----------------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_CommitParametersToCameraDevice( PicamHandle model );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RefreshParameterFromCameraDevice(
    PicamHandle    model,
    PicamParameter parameter );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RefreshParametersFromCameraDevice(
    PicamHandle model );
/*----------------------------------------------------------------------------*/

/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/* Camera Data Acquisition                                                    */
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/
/******************************************************************************/

/*----------------------------------------------------------------------------*/
/* Camera Acquisition Setup - Buffer -----------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef struct PicamAcquisitionBuffer
{
    void* memory;
    pi64s memory_size;
} PicamAcquisitionBuffer;
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_GetAcquisitionBuffer(
    PicamHandle             device,
    PicamAcquisitionBuffer* buffer );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_SetAcquisitionBuffer(
    PicamHandle                   device,
    const PicamAcquisitionBuffer* buffer );
/*----------------------------------------------------------------------------*/
/* Camera Notification -------------------------------------------------------*/
/*----------------------------------------------------------------------------*/
/* Camera Notification - Acquisition -----------------------------------------*/
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamAcquisitionUpdatedCallback)(
    PicamHandle                   device,
    const PicamAvailableData*     available,
    const PicamAcquisitionStatus* status );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForAcquisitionUpdated(
    PicamHandle                     device,
    PicamAcquisitionUpdatedCallback updated ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForAcquisitionUpdated(
    PicamHandle                     device,
    PicamAcquisitionUpdatedCallback updated ); /* ASYNC */
/*----------------------------------------------------------------------------*/
/* Camera Notification - Acquisition States ----------------------------------*/
/*----------------------------------------------------------------------------*/
typedef enum PicamAcquisitionState
{
    PicamAcquisitionState_ReadoutStarted = 1,
    PicamAcquisitionState_ReadoutEnded   = 2
} PicamAcquisitionState; /* (3) */
/*----------------------------------------------------------------------------*/
typedef enum PicamAcquisitionStateErrorsMask
{
    PicamAcquisitionStateErrorsMask_None      = 0x0,
    PicamAcquisitionStateErrorsMask_LostCount = 0x1
} PicamAcquisitionStateErrorsMask; /* (0x2) */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_CanRegisterForAcquisitionStateUpdated(
    PicamHandle           device,
    PicamAcquisitionState state,
    pibln*                detectable );
/*----------------------------------------------------------------------------*/
typedef struct PicamAcquisitionStateCounters
{
    pi64s readout_started_count;
    pi64s readout_ended_count;
} PicamAcquisitionStateCounters;
/*----------------------------------------------------------------------------*/
typedef PicamError (PIL_CALL* PicamAcquisitionStateUpdatedCallback)(
    PicamHandle                          device,
    PicamAcquisitionState                current,
    const PicamAcquisitionStateCounters* counters,
    PicamAcquisitionStateErrorsMask      errors );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_RegisterForAcquisitionStateUpdated(
    PicamHandle                          device,
    PicamAcquisitionState                state,
    PicamAcquisitionStateUpdatedCallback updated ); /* ASYNC */
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_UnregisterForAcquisitionStateUpdated(
    PicamHandle                          device,
    PicamAcquisitionState                state,
    PicamAcquisitionStateUpdatedCallback updated ); /* ASYNC */
/*----------------------------------------------------------------------------*/
/* Camera Acquisition Control ------------------------------------------------*/
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_HasAcquisitionBufferOverrun(
    PicamHandle device,
    pibln*      overran );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_CanClearReadoutCountOnline(
    PicamHandle device,
    pibln*      clearable );
/*----------------------------------------------------------------------------*/
PICAM_API PicamAdvanced_ClearReadoutCountOnline(
    PicamHandle device,
    pibln*      cleared );
/*----------------------------------------------------------------------------*/

/******************************************************************************/
/* C++ Epilogue                                                               */
/******************************************************************************/
#if defined __cplusplus && !defined PICAM_EXPORTS
    }   /* end extern "C" */
#endif

#endif
