/**
 * @file    stm32f1xx_it.c
 * @brief   中断处理函数 (SysTick / TIM4 控制 / CAN 接收)
 */

#include "stm32f1xx_hal.h"
#include "stm32f1xx_it.h"
#include "../../app/control_loop.h"
#include "../../common/can_protocol/can_protocol.h"

extern TIM_HandleTypeDef htim4;
extern CAN_HandleTypeDef hcan;

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void TIM4_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim4);
}

/* CAN 接收中断: 收到指令帧 */
void CAN_RX0_IRQHandler(void)
{
    HAL_CAN_IRQHandler(&hcan);
}

void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan_ptr)
{
    CAN_RxHeaderTypeDef header;
    uint8_t data[8] = {0};
    if (HAL_CAN_GetRxMessage(hcan_ptr, CAN_RX_FIFO0, &header, data) == HAL_OK) {
        if (header.StdId == CAN_ID_COMMAND) {  /* 只处理指令帧 0x100 */
            control_loop_on_can_rx(data);
        }
    }
}
