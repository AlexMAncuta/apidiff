package org.example.apimock.service;

import jakarta.annotation.PostConstruct;
import org.example.apimock.entity.Category;
import org.example.apimock.entity.Product;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class ProductService {

    private final List<Product> products = new ArrayList<>();
    private final AtomicLong idCounter = new AtomicLong(1);

    @PostConstruct
    public void init() {
        products.add(new Product(idCounter.getAndIncrement(), "Laptop", "SKU-1001",
                new BigDecimal("4500.00"), "RON", Category.ELECTRONICS, true, 12));
        products.add(new Product(idCounter.getAndIncrement(), "T-Shirt", "SKU-1002",
                new BigDecimal("89.99"), "RON", Category.CLOTHING, true, 140));
        products.add(new Product(idCounter.getAndIncrement(), "Coffee", "SKU-1003",
                new BigDecimal("55.00"), "RON", Category.FOOD, false, 0));
        products.add(new Product(idCounter.getAndIncrement(), "Clean Code", "SKU-1004",
                new BigDecimal("150.00"), "RON", Category.BOOKS, true, 7));
    }

    public List<Product> findAll(Category category, Boolean available) {
        List<Product> result = new ArrayList<>();
        for (Product p : products) {
            if (category != null && p.getCategory() != category) {
                continue;
            }
            if (available != null && !available.equals(p.getAvailable())) {
                continue;
            }
            result.add(p);
        }
        return result;
    }

    public List<Product> searchByName(String name) {
        List<Product> result = new ArrayList<>();
        for (Product p : products) {
            if (p.getName().toLowerCase().contains(name.toLowerCase())) {
                result.add(p);
            }
        }
        return result;
    }

    public List<Product> findSimilar(Long id) {
        Product target = findById(id);
        if (target == null) {
            return null;
        }
        List<Product> result = new ArrayList<>();
        for (Product p : products) {
            if (!p.getId().equals(id) && p.getCategory() == target.getCategory()) {
                result.add(p);
            }
        }
        return result;
    }

    public Product findById(Long id) {
        for (Product p : products) {
            if (p.getId().equals(id)) {
                return p;
            }
        }
        return null;
    }

    public Product create(Product product) {
        product.setId(idCounter.getAndIncrement());
        products.add(product);
        return product;
    }

    public Product update(Long id, Product product) {
        Product existing = findById(id);
        if (existing == null) {
            return null;
        }
        existing.setName(product.getName());
        existing.setSku(product.getSku());
        existing.setPrice(product.getPrice());
        existing.setCurrency(product.getCurrency());
        existing.setCategory(product.getCategory());
        existing.setAvailable(product.getAvailable());
        existing.setStockQuantity(product.getStockQuantity());
        return existing;
    }
}