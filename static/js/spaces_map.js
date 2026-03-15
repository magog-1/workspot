window.WorkspotMap = (function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function toNumber(v) {
    var n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function init(config) {
    var spaces = Array.isArray(config.spaces) ? config.spaces : [];
    var uiMode = config.uiMode || "list";
    var selectedSpaceId = config.selectedSpaceId || null;

    var mapRoot = byId("map");
    if (!mapRoot) {
      return;
    }

    function showMapError(message) {
      mapRoot.innerHTML =
        '<div class="map-placeholder bg-secondary text-white text-center p-4 rounded h-100 d-flex align-items-center justify-content-center">' +
        '<div><div class="fs-5 mb-2">🗺 Карта недоступна</div><div class="small">' + message + '</div></div>' +
        "</div>";
    }

    if (typeof ymaps === "undefined") {
      showMapError("Не удалось загрузить API Яндекс Карт. Обновите страницу или проверьте ключ/API-доступ.");
      return;
    }

    ymaps.ready(function () {
      try {
        var MOSCOW_CENTER = [55.7558, 37.6176];
        var DEFAULT_ZOOM = uiMode === "map" ? 11 : 10;

        var map = new ymaps.Map("map", {
          center: MOSCOW_CENTER,
          zoom: DEFAULT_ZOOM,
          controls: ["zoomControl", "fullscreenControl", "typeSelector"]
        });

      var pointsById = {};
      var route = null;
      var originCoords = null;
      var destination = null;
      var pickOriginMode = false;
      var originMode = "none";

      var originMarker = null;

      function ensureOriginMarker() {
        if (originMarker) return originMarker;
        originMarker = new ymaps.Placemark(MOSCOW_CENTER, {}, {
          preset: "islands#greenDotIcon"
        });
        return originMarker;
      }

      function clearRoute() {
        if (route) {
          map.geoObjects.remove(route);
          route = null;
        }
      }

      function drawRouteIfReady() {
        clearRoute();
        if (!originCoords || !destination) {
          return;
        }
        ymaps.route([
          originCoords,
          [destination.latitude, destination.longitude]
        ], {
          mapStateAutoApply: true
        }).then(function (r) {
          route = r;
          map.geoObjects.add(route);
        }).catch(function () {
          // ignore route errors, UI state stays as is
        });
      }

      function setOrigin(coords) {
        originCoords = coords;
        var marker = ensureOriginMarker();
        marker.geometry.setCoordinates(coords);
        if (!marker.__addedToMap) {
          map.geoObjects.add(marker);
          marker.__addedToMap = true;
        }
        drawRouteIfReady();
      }

      function setDestination(space) {
        destination = space;
        drawRouteIfReady();

        var active = document.querySelector(".ws-space-option.active");
        if (active) active.classList.remove("active");
        var card = document.querySelector('.ws-space-option[data-space-id="' + space.id + '"]');
        if (card) card.classList.add("active");
      }

        function updatePickModeUI() {
        var btn = byId("pickOriginBtn");
        var geolocBtn = byId("useMyLocationBtn");
        var status = byId("originModeStatus");

        if (btn) {
          btn.classList.toggle("btn-warning", pickOriginMode);
          btn.classList.toggle("btn-outline-warning", !pickOriginMode);
          btn.classList.toggle("active", pickOriginMode);
        }

        if (geolocBtn) {
          var geolocActive = originMode === "geolocation";
          geolocBtn.classList.toggle("btn-success", geolocActive);
          geolocBtn.classList.toggle("btn-outline-success", !geolocActive);
          geolocBtn.classList.toggle("active", geolocActive);
        }

        if (status) {
          if (pickOriginMode) {
            status.textContent = "Режим: выберите старт кликом по карте";
            status.className = "small text-warning";
          } else if (originMode === "geolocation") {
            status.textContent = "Режим: старт = текущее местоположение";
            status.className = "small text-success";
          } else if (originMode === "address") {
            status.textContent = "Режим: старт = адрес из поиска";
            status.className = "small text-primary";
          } else if (originMode === "map") {
            status.textContent = "Режим: старт выбран на карте";
            status.className = "small text-warning";
          } else {
            status.textContent = "Режим: старт не выбран";
            status.className = "small text-muted";
          }
        }

          var mapContainerElement = map.container && map.container.getElement ? map.container.getElement() : null;
          if (mapContainerElement) {
            mapContainerElement.style.cursor = pickOriginMode ? "crosshair" : "";
          }
        }

        spaces.forEach(function (s) {
        if (s.latitude == null || s.longitude == null) return;

        pointsById[s.id] = s;

        var pm = new ymaps.Placemark(
          [s.latitude, s.longitude],
          {
            balloonContentHeader: "<strong>" + s.name + "</strong>",
            balloonContentBody: "📍 " + s.address + "<br>💰 " + s.price_per_hour + " ₽/час",
            balloonContentFooter:
              "<a href='/spaces/" + s.id + "' style='color:#0d6efd;font-weight:500'>Подробнее →</a>",
            hintContent: s.name
          },
          { preset: "islands#blueStretchyIcon" }
        );

        pm.events.add("click", function () {
          setDestination(s);
        });

        map.geoObjects.add(pm);
      });

        updatePickModeUI();

        if (selectedSpaceId && pointsById[selectedSpaceId]) {
          setDestination(pointsById[selectedSpaceId]);
        }

        var useMyLocationBtn = byId("useMyLocationBtn");
        if (useMyLocationBtn) {
          useMyLocationBtn.addEventListener("click", function () {
            if (!navigator.geolocation) return;
            navigator.geolocation.getCurrentPosition(function (position) {
              originMode = "geolocation";
              pickOriginMode = false;
              setOrigin([position.coords.latitude, position.coords.longitude]);
              map.setCenter([position.coords.latitude, position.coords.longitude], 13, { checkZoomRange: true });
              updatePickModeUI();
            });
          });
        }

        var findAddressBtn = byId("findAddressBtn");
        var originAddressInput = byId("originAddressInput");
        if (findAddressBtn && originAddressInput) {
          findAddressBtn.addEventListener("click", function () {
            var q = (originAddressInput.value || "").trim();
            if (!q) return;
            ymaps.geocode(q).then(function (res) {
              var first = res.geoObjects.get(0);
              if (!first) return;
              var coords = first.geometry.getCoordinates();
              originMode = "address";
              pickOriginMode = false;
              setOrigin(coords);
              map.setCenter(coords, 13, { checkZoomRange: true });
              updatePickModeUI();
            }).catch(function () {
              // ignore geocode errors
            });
          });
        }

        var pickOriginBtn = byId("pickOriginBtn");
        if (pickOriginBtn) {
          pickOriginBtn.addEventListener("click", function () {
            pickOriginMode = !pickOriginMode;
            updatePickModeUI();
          });
        }

        map.events.add("click", function (e) {
          if (!pickOriginMode) return;
          var coords = e.get("coords");
          originMode = "map";
          setOrigin(coords);
          pickOriginMode = false;
          updatePickModeUI();
        });

        var clearRouteBtn = byId("clearRouteBtn");
        if (clearRouteBtn) {
          clearRouteBtn.addEventListener("click", function () {
            clearRoute();
            destination = null;
            originCoords = null;
            pickOriginMode = false;
            originMode = "none";
            if (originMarker && originMarker.__addedToMap) {
              map.geoObjects.remove(originMarker);
              originMarker.__addedToMap = false;
            }
            map.setCenter(MOSCOW_CENTER, DEFAULT_ZOOM, { checkZoomRange: true });
            updatePickModeUI();
            var active = document.querySelector(".ws-space-option.active");
            if (active) active.classList.remove("active");
          });
        }

        document.querySelectorAll(".js-set-destination").forEach(function (btn) {
          btn.addEventListener("click", function () {
            var id = btn.dataset.spaceId;
            var lat = toNumber(btn.dataset.lat);
            var lon = toNumber(btn.dataset.lon);
            if (!id || lat == null || lon == null) return;

            var fromPoint = pointsById[id] || {
              id: id,
              name: btn.dataset.name || "Коворкинг",
              latitude: lat,
              longitude: lon
            };
            setDestination(fromPoint);
            map.setCenter([lat, lon], 14, { checkZoomRange: true });
          });
        });

      } catch (err) {
        showMapError("Ошибка инициализации карты. Проверьте API-ключ или консоль браузера.");
      }
    });
  }

  return { init: init };
})();
