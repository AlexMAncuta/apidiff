package org.example.apimock.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class Product {

    private Long id;
    private String name;
    private String sku;
    private BigDecimal price;
    private String currency;
    private Category category;
    private Boolean available;
    private Integer stockQuantity;

}