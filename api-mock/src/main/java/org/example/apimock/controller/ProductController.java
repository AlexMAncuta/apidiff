package org.example.apimock.controller;

import org.example.apimock.entity.Category;
import org.example.apimock.entity.Product;
import org.example.apimock.service.ProductService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    public List<Product> getAll(
            @RequestParam(required = false) Category category,
            @RequestParam(required = false) Boolean available) {
        return productService.findAll(category, available);
    }

    @GetMapping("/search")
    public List<Product> search(@RequestParam String name) {
        return productService.searchByName(name);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Product> getById(@PathVariable Long id) {
        Product product = productService.findById(id);
        if (product == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(product);
    }

    @GetMapping("/{id}/similar")
    public ResponseEntity<List<Product>> getSimilar(@PathVariable Long id) {
        List<Product> similar = productService.findSimilar(id);
        if (similar == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(similar);
    }

    @PostMapping
    public Product create(@RequestBody Product product) {
        return productService.create(product);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Product> update(@PathVariable Long id, @RequestBody Product product) {
        Product updated = productService.update(id, product);
        if (updated == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(updated);
    }

    @GetMapping("/health")
    public String health() {
        return "Healthy";
    }
}