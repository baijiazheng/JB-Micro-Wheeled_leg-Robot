/**
 * @file    can_bus.c
 * @brief   CAN 总线驱动实现 (STM32F103 bxCAN, 500kbps)
 */

#include "can_bus.h"
#include "stm32f1xx_hal.h"

void can_bus_init(CanBus *bus, void *hcan)
{
    bus->hcan = hcan;
    bus->rx_new = 0;
    bus->rx_cmd.linear_vel = 0;
    bus->rx_cmd.angular_vel = 0;
    bus->rx_cmd.estop = 1; /* 默认急停, 收到指令才解锁 */
}

int can_bus_send_status(CanBus *bus, const CanStatus *st)
{
    CAN_HandleTypeDef *hcan = (CAN_HandleTypeDef *)bus->hcan;
    uint8_t data[8];
    uint32_t mailbox;
    CAN_TxHeaderTypeDef header;

    can_encode_status(st, data);

    header.StdId = CAN_ID_STATUS;
    header.ExtId = 0;
    header.IDE = CAN_ID_STD;
    header.RTR = CAN_RTR_DATA;
    header.DLC = 8;
    header.TransmitGlobalTime = DISABLE;

    if (HAL_CAN_AddTxMessage(hcan, &header, data, &mailbox) != HAL_OK) {
        return -1;
    }
    return 0;
}

void can_bus_on_rx(CanBus *bus, const uint8_t data[8])
{
    can_decode_command(data, &bus->rx_cmd);
    bus->rx_new = 1;
}
