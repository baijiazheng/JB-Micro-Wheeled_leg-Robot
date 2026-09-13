/**
 * @file    can_bus.h
 * @brief   CAN 总线驱动 (驱动板从机: 收指令 0x100, 发状态 0x200)
 */

#ifndef CAN_BUS_H
#define CAN_BUS_H

#include <stdint.h>
#include "can_protocol.h"  /* 经 Makefile -I ../common/can_protocol 找到 */

typedef struct {
    void *hcan;           /* CAN_HandleTypeDef* */
    CanCommand rx_cmd;    /* 收到的指令 */
    volatile uint8_t rx_new;  /* 收到新指令标志 */
} CanBus;

/** 初始化 CAN (500kbps) */
void can_bus_init(CanBus *bus, void *hcan);

/** 发送状态帧 */
int can_bus_send_status(CanBus *bus, const CanStatus *st);

/** 收到指令帧时在 HAL 回调里调用本函数 */
void can_bus_on_rx(CanBus *bus, const uint8_t data[8]);

#endif /* CAN_BUS_H */
