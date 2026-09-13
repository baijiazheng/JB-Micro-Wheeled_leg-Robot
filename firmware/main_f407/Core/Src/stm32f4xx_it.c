/**
 * @file    stm32f4xx_it.c
 * @brief   中断处理 (SysTick / CAN1 接收)
 */

#include "stm32f4xx_hal.h"
#include "../../app/main_control.h"
#include "../../common/can_protocol/can_protocol.h"

extern CAN_HandleTypeDef hcan1;

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void CAN1_RX0_IRQHandler(void)
{
    HAL_CAN_IRQHandler(&hcan1);
}

void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan_ptr)
{
    CAN_RxHeaderTypeDef header;
    uint8_t data[8] = {0};
    if (HAL_CAN_GetRxMessage(hcan_ptr, CAN_RX_FIFO0, &header, data) == HAL_OK) {
        if (header.StdId == CAN_ID_STATUS) {  /* 状态帧 0x200 */
            main_control_on_can_rx(data);
        }
    }
}
